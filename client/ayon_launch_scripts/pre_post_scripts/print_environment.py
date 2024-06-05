import os

print("Start of current environment")
for key, value in sorted(os.environ.items()):
    print(f"{key} = {value}")
print("End of current environment")
