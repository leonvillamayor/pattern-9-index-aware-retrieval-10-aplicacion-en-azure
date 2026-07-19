from opentelemetry import trace
from opentelemetry.exporter.azuremonitor import AzureMonitorSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semtrace import SpanAttributes

provider = TracerProvider()
exporter = AzureMonitorSpanExporter(
    connection_string="InstrumentationKey=<YOUR_KEY>;IngestionEndpoint=https://<region>.in.applicationinsights.io/"
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("pattern9.azure")

with tracer.start_as_current_span("retrieval.segment") as span:
    span.set_attribute("retrieval.model_version", f"{deployment}@{api_version}")
    span.set_attribute("retrieval.embedder.dim", int(embed_dim))
    span.set_attribute("retrieval.segment.id", segment_id)
    span.set_attribute("cloud_provider", "azure")