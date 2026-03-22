# Multilingual Datasets

Place multilingual workflow files in this folder for production imports:

- `nyaysaathi_en.json`
- `nyaysaathi_hi.json`
- `nyaysaathi_mr.json`

Then run from `backend/`:

```bash
python scripts/import_multilingual_data.py --wipe
```

The importer also supports current repository fallback paths if these files are not present.
