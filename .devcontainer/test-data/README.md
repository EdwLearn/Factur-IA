# Test Data Directory

This directory contains test data, fixtures, and sample files for the FacturIA testing environment.

## Structure

```
test-data/
├── fixtures/               # JSON fixtures for tests
│   └── sample-invoice.json
├── sample-invoices/        # Sample PDF/image files
│   └── (add your test invoice files here)
└── seed-db.sql            # Database seed data
```

## Usage

### Database Seeding

The `seed-db.sql` file is automatically run when the test environment is initialized:

```bash
./.devcontainer/scripts/setup-test-env.sh
```

This creates sample invoices and line items in the test database.

### JSON Fixtures

The JSON fixtures in the `fixtures/` directory can be used in tests:

```python
# Python example
import json

def load_fixture(name):
    with open(f'.devcontainer/test-data/fixtures/{name}.json') as f:
        return json.load(f)

# Usage
sample_invoices = load_fixture('sample-invoice')
```

```typescript
// TypeScript example
import sampleInvoices from '@/../.devcontainer/test-data/fixtures/sample-invoice.json';

// Usage in tests
const testInvoice = sampleInvoices.invoices[0];
```

### Sample Invoices

Place sample PDF or image files in the `sample-invoices/` directory. These are automatically uploaded to LocalStack S3 during environment setup.

Recommended test files:
- `sample-invoice-1.pdf` - Standard invoice format
- `sample-invoice-2.pdf` - Multi-page invoice
- `sample-invoice-scanned.jpg` - Scanned document
- `sample-invoice-poor-quality.png` - Low quality image for OCR testing

## Adding New Test Data

### Adding Database Fixtures

1. Edit `seed-db.sql`
2. Add your INSERT statements
3. Restart the test environment or run:
   ```bash
   PGPASSWORD=test_password psql -h localhost -p 5433 -U test_user -d facturia_test -f .devcontainer/test-data/seed-db.sql
   ```

### Adding JSON Fixtures

1. Create a new JSON file in `fixtures/`
2. Follow the existing structure
3. Document the fixture purpose in this README

### Adding Sample Files

1. Place files in `sample-invoices/`
2. Run setup script to upload to S3:
   ```bash
   ./.devcontainer/scripts/setup-test-env.sh
   ```

## Best Practices

- Keep test data realistic but anonymized
- Use consistent naming conventions (test-*, fixture-*, sample-*)
- Document any special test cases or edge cases
- Keep file sizes reasonable (< 5MB per file)
- Use version control for text fixtures (JSON, SQL)
- Don't commit large binary files - document where to obtain them instead

## Cleaning Up

To reset the test database:

```bash
# Drop and recreate the database
PGPASSWORD=test_password psql -h localhost -p 5433 -U test_user -d postgres -c "DROP DATABASE IF EXISTS facturia_test;"
PGPASSWORD=test_password psql -h localhost -p 5433 -U test_user -d postgres -c "CREATE DATABASE facturia_test;"

# Re-run migrations and seed
cd apps/api && alembic upgrade head && cd ../..
./.devcontainer/scripts/setup-test-env.sh
```

To clean S3 test data:

```bash
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test aws --endpoint-url=http://localhost:4567 s3 rm s3://facturia-test-documents --recursive
```
