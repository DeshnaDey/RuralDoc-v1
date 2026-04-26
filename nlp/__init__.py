# nlp/ — ML pattern recognition layer for RuralDoc patient intake
#
# Modules:
#   vocab.py        SymptomVocab — in-memory symptom cache + pgvector matcher
#   extractor.py    SymptomExtractor — LLM structured extraction → ParsedComplaint
#   matcher.py      match ParsedComplaint against SymptomVocab
#   auto_migrate.py upsert novel symptoms to DB, write patient_history_events
