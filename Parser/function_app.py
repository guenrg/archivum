import json
import logging

import azure.functions as func

from _core import extract_bytes, get_client, get_extract_config_id, map_to_catalog_dto
from _db import get_supabase_client, get_auction_company_id, save_catalog

app = func.FunctionApp()


@app.blob_trigger(
    arg_name="inputblob",
    path="input-pdfs/{name}.pdf",
    connection="AzureWebJobsStorage",
    source="EventGrid",
)
@app.blob_output(
    arg_name="outputblob",
    path="output-json/{name}.json",
    connection="AzureWebJobsStorage",
)
def process_auction_pdf(inputblob: func.InputStream, outputblob: func.Out[str]) -> None:
    """Triggered when a PDF is uploaded to the 'input-pdfs' container.

    Runs LlamaExtract on the PDF, writes the raw extracted JSON to the
    'output-json' container, and persists the catalog to Supabase.
    """
    blob_name = inputblob.name or "unknown"
    filename = blob_name.split("/")[-1]
    logging.info("Processing blob: %s (%s bytes)", blob_name, inputblob.length)

    # Extract structured data via LlamaExtract (v2)
    client = get_client()
    config_id = get_extract_config_id()
    data = extract_bytes(client, config_id, inputblob.read(), filename)

    # Write the raw extracted JSON to the output container
    outputblob.set(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    logging.info("Saved extracted JSON for: %s", filename)

    # Map extracted data into DTOs
    catalog = map_to_catalog_dto(data)
    logging.info(
        "Mapped catalog: publication %s, %d section(s)",
        catalog.details.publicationNumber,
        len(catalog.sections),
    )

    # Persist the catalog to Supabase
    supabase_client = get_supabase_client()
    company_id = get_auction_company_id()
    auction_id = save_catalog(supabase_client, catalog, company_id)
    listing_count = sum(len(section.listings) for section in catalog.sections)
    logging.info(
        "Saved auction %s to Supabase (publication %s, %d listing(s))",
        auction_id,
        catalog.details.publicationNumber,
        listing_count,
    )