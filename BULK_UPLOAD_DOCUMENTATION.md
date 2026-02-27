# CSV Bulk Upload for Event Goers

## Overview

This feature allows you to bulk upload contacts (event goers) from a CSV file to your event management system. Perfect for importing customer lists from email marketing platforms, CRM systems, or other sources.

## Endpoint

**POST** `/api/event-goers/bulk-upload?on_duplicate=skip`

### Parameters

- **file** (required): CSV file to upload
- **on_duplicate** (optional): Action when duplicate emails are found
  - `skip` (default): Skip existing contacts
  - `update`: Update existing contacts with new data

## CSV Format

### Required Columns

| Column | Description | Example |
|--------|-------------|---------|
| email | Email address (must be valid) | john.doe@example.com |
| name | Full name | John Doe |

### Optional Columns

| Column | Description | Example | Default |
|--------|-------------|---------|---------|
| phone | Phone number | +1-555-0101 | - |
| birthdate | Date in YYYY-MM-DD format | 1990-05-15 | - |
| email_opt_in | Email subscription preference | true/false | true |
| sms_opt_in | SMS subscription preference | true/false | false |
| marketing_opt_in | Marketing email preference | true/false | false |

### Sample CSV File

```csv
email,name,phone,birthdate,email_opt_in,sms_opt_in,marketing_opt_in
john.doe@example.com,John Doe,+1-555-0101,1990-05-15,true,false,true
jane.smith@example.com,Jane Smith,+1-555-0102,1985-08-22,true,false,true
bob.wilson@example.com,Bob Wilson,+1-555-0103,,false,false,false
alice.brown@example.com,Alice Brown,+1-555-0104,1992-12-01,true,true,true
```

## Usage Examples

### Using curl

```bash
# Upload with skip duplicates (default)
curl -X POST "http://127.0.0.1:8080/api/event-goers/bulk-upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@contacts.csv" \
  -F "on_duplicate=skip"

# Upload with update duplicates
curl -X POST "http://127.0.0.1:8080/api/event-goers/bulk-upload?on_duplicate=update" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@contacts.csv"
```

### Using Python requests

```python
import requests

url = "http://127.0.0.1:8080/api/event-goers/bulk-upload"
files = {'file': open('contacts.csv', 'rb')}
params = {'on_duplicate': 'skip'}  # or 'update'

response = requests.post(url, files=files, params=params)
result = response.json()

print(f"Created: {result['created']}")
print(f"Updated: {result['updated']}")
print(f"Skipped: {result['skipped']}")
print(f"Errors: {result['errors']}")

if result['error_details']:
    print("\nErrors:")
    for error in result['error_details']:
        print(f"  Row {error['row']}: {error['error']} - {error['email']}")
```

### Using JavaScript fetch

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://127.0.0.1:8080/api/event-goers/bulk-upload?on_duplicate=skip', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(result => {
  console.log(`Created: ${result.created}`);
  console.log(`Updated: ${result.updated}`);
  console.log(`Skipped: ${result.skipped}`);
  console.log(`Errors: ${result.errors}`);

  if (result.error_details) {
    console.log('Errors:', result.error_details);
  }
});
```

## Response Format

```json
{
  "created": 10,
  "updated": 5,
  "skipped": 2,
  "errors": 1,
  "error_details": [
    {
      "row": 15,
      "error": "Invalid email format",
      "email": "invalid-email"
    }
  ],
  "total_rows": 18
}
```

### Response Fields

- **created**: Number of new contacts created
- **updated**: Number of existing contacts updated (only when `on_duplicate=update`)
- **skipped**: Number of duplicate contacts skipped (only when `on_duplicate=skip`)
- **errors**: Total number of rows with errors
- **error_details**: Array of specific error details
  - **row**: Row number in CSV file
  - **error**: Error message
  - **email**: Email from the problematic row
- **total_rows**: Total number of rows processed (excluding header)

## Common Errors

### Missing Required Fields
```
"error": "Missing required fields (email or name)"
```
Solution: Ensure both email and name columns have values.

### Invalid Email Format
```
"error": "Invalid email format"
```
Solution: Ensure email column contains valid email addresses (e.g., user@domain.com).

### Invalid Date Format
```
Birthdate will be silently skipped if format is incorrect
```
Solution: Use YYYY-MM-DD format for birthdates (e.g., 1990-05-15).

## Best Practices

1. **Clean Your Data First**: Remove duplicates, validate emails, and standardize phone formats before uploading.

2. **Start with Skip Mode**: Use `on_duplicate=skip` first to avoid accidentally updating existing contacts.

3. **Review Error Details**: Always check `error_details` in the response to identify and fix data issues.

4. **Batch Large Files**: For files with thousands of contacts, consider splitting into smaller batches (500-1000 contacts each).

5. **Test with Sample**: Always test with a small sample file before uploading large datasets.

6. **Backup Database**: Consider backing up your database before bulk operations, especially when using `on_duplicate=update`.

## CSV Tips

- **Delimiters**: The endpoint supports both comma (`,`) and semicolon (`;`) as delimiters.
- **Headers**: Column names are case-insensitive and extra spaces are trimmed.
- **Empty Values**: Leave optional columns empty rather than using "N/A" or "null".
- **Boolean Values**: Use `true`, `1`, or `yes` for true; `false`, `0`, or `no` for false.

## Integration Examples

### Export from Mailchimp

1. Export your audience as CSV from Mailchimp
2. Map columns:
   - `Email Address` → `email`
   - `First Name` + `Last Name` → `name`
   - `Phone Number` → `phone`
3. Clean up the CSV header to match required format
4. Upload using the endpoint

### Export from HubSpot

1. Export contacts from HubSpot as CSV
2. Map columns:
   - `Email` → `email`
   - `First Name` + `Last Name` → `name`
   - `Phone Number` → `phone`
   - `Lifecycle Stage` → Consider using for segmentation
3. Upload using the endpoint

### Export from Excel

1. Save your Excel file as CSV (Comma delimited)
2. Ensure first row contains headers
3. Verify email and name columns are filled
4. Upload using the endpoint
