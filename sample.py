import os

def get_csv_filenames(directory):
    return [f.replace('.csv', '') for f in os.listdir(directory) if f.endswith('.csv')]

# Example usage:
csv_files = get_csv_filenames('sector_files')
print(csv_files)
