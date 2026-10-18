"""Download the Cookie Cats A/B test dataset (about 2.5 MB) into data/raw/."""
from pathlib import Path
from urllib.request import urlretrieve

URL = "https://raw.githubusercontent.com/robguilarr/ab_testing_cookie_cats/main/datasets/cookie_cats.csv"
dest = Path(__file__).resolve().parents[1] / "data" / "raw" / "cookie_cats.csv"
dest.parent.mkdir(parents=True, exist_ok=True)
urlretrieve(URL, dest)
print(f"Saved {dest}")
