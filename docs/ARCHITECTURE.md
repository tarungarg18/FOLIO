# Architecture

FOLIO uses a small local architecture: a Next.js client talks to one FastAPI service, which owns authorization, calculations, ingestion metadata, and Gemini calls. The service uses PyMongo to access local MongoDB Community Server. Python scripts load source data into the same database. Docker is optional.

See `planning/ARCHITECTURE_AND_DEPENDENCIES.md` for the design blueprint. Current implemented endpoints and limitations are described in the API docs.
