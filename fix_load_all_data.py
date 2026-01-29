# fix_load_all_data.py

file_path = "app.py"
old_call = "load_all_data(skip_statcast=True)"
new_call = "load_all_data()"

# Read the contents of the file
with open(file_path, "r") as file:
    lines = file.readlines()

# Replace the line if found
modified = False
with open(file_path, "w") as file:
    for line in lines:
        if old_call in line:
            line = line.replace(old_call, new_call)
            modified = True
        file.write(line)

if modified:
    print(f"✅ Replaced '{old_call}' with '{new_call}' in {file_path}")
else:
    print(f"ℹ️ No occurrences of '{old_call}' found in {file_path}")
