import csv

class SuperCSV:
    def __init__(self, filename):
        self.filename = filename
        self.metadata = []  # List of (key, value) pairs
        self.column_headers = []
        self.column_defaults = {}  # Dictionary to store default values per column
        self.rows = []

    def set_metadata(self, metadata):
        """Accepts a list of (key, value) tuples for metadata."""
        self.metadata = list(metadata)

    def set_columns(self, headers_with_defaults):
        """Accepts a list of (column_name, default_value) tuples."""
        self.column_headers = [col for col, _ in headers_with_defaults]
        self.column_defaults = {col: default for col, default in headers_with_defaults}

    def add_row(self, row):
        """Adds a row, filling in missing values with defaults."""
        complete_row = {
            col: row.get(col, self.column_defaults.get(col, ''))
            for col in self.column_headers
        }
        self.rows.append(complete_row)

    def get_row(self, index):
        return self.rows[index] if 0 <= index < len(self.rows) else None

    def set_row(self, index, row):
        if 0 <= index < len(self.rows):
            complete_row = {
                col: row.get(col, self.column_defaults.get(col, ''))
                for col in self.column_headers
            }
            self.rows[index] = complete_row

    def read(self):
        with open(self.filename, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            section = 'metadata'
            for line in reader:
                if not line:
                    continue
                if line[0].strip() == '[DATA]':
                    section = 'data'
                    self.column_headers = next(reader)
                    continue
                if section == 'metadata':
                    if len(line) >= 2:
                        self.metadata.append((line[0].strip(), line[1].strip()))
                elif section == 'data':
                    self.rows.append({col: val for col, val in zip(self.column_headers, line)})

    def write(self):
        with open(self.filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for key, val in self.metadata:
                writer.writerow([key, val])
            writer.writerow(['[DATA]'])
            writer.writerow(self.column_headers)
            for row in self.rows:
                writer.writerow([row.get(col, self.column_defaults.get(col, '')) for col in self.column_headers])
