import matplotlib.pyplot as plt
import json
with open("output_data.json", "r") as f:
    data = json.load(f)

bands = []
hayScores = []
for item in data:
    bands.append(item["band"])
    hayScores.append(item["hayScore"])
plt.plot(bands, hayScores, "o-", color="blue")
plt.xlabel("Band")
plt.ylabel("Hay Score")
plt.title("Hay Score by Band")
plt.grid(True)
plt.show()
