from azure.eventhub import EventHubProducerClient, EventDataBatch
import json, datetime as dt

producer = EventHubProducerClient.from_connection_string(
    conn_str="Endpoint=sb://rag-prod.servicebus.windows.net/;...",
    eventhub_name="retrieval-feedback",
    partition_key=dt.date.today().isoformat()  # p.ej. "2026-01-14"
)

batch = producer.create_batch()
batch.add(EventData(json.dumps({
    "query_id": "q-7821",
    "pred_conf": 0.91,
    "label": 1,
    "model_version": "text-embedding-3-large@2024-05-01-preview",
    "embed_dim": 512,
    "domain": "legal-es"
})))
producer.send_batch(batch)