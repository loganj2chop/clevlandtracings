####How to run:

#python manage_tracings_no_pred.py \
#  --txt_dir /path/to/txt/files \
 # --metadata_csv metadata.csv

#### /Users/loganj2/Desktop/Txt_files/VUDSTest.csv

### /Users/loganj2/Desktop/Txt_files/txt_files
#!/usr/bin/env python3

#!/usr/bin/env python3
import os
import argparse
import pandas as pd
import numpy as np


class ManageTracingsNoPred:
    def __init__(self, file_path, df):
        self.file_path = file_path
        self.df = df

    def run(self):
        outer = []
        print(self.file_path)

        files = os.listdir(self.file_path)
        print(files)
        files_txt = [f for f in files if f.endswith(".txt")]

        for file in files_txt:
            print(file)
            file_study_id = file.split(".")[0]
            print(f"File study_id: {file_study_id}")

            # match metadata row
            meta = self.df[self.df["study_id"].astype(str) == file_study_id]
            if meta.empty:
                continue

            row = meta.iloc[0]
            myfile = os.path.join(self.file_path, file)
            print(f"Processing {myfile}")

            dfarr = pd.read_csv(myfile, sep="\t")

            # percent normalization
            dfarr["percent"] = (dfarr["VH2O"] / row["ebc"]).round(2)
            dfarr = dfarr.loc[(dfarr["percent"] >= 0.01) & (dfarr["percent"] <= 1.0)]

            # aggregate
            dfarr = (
                dfarr[["Pdet", "percent"]]
                .groupby("percent", as_index=False)["Pdet"]
                .mean()
                .drop(columns=["percent"])
            )

            # transpose
            df1 = dfarr.transpose().reset_index(drop=True)

            # insert study_id as FIRST column
            df1.insert(0, "study_id", row["study_id"])

            outer.append(df1)

        # ------------------------------------------------
        # OUTPUT
        # ------------------------------------------------
        if not outer:
            raise RuntimeError("No matching tracing files were processed.")

        finaldf = pd.concat(outer, ignore_index=True)
        finaldf.to_csv("vudstracings.csv", index=False)
        print("Saved vudstracings.csv")


# ======================================================
# ARGPARSE ENTRYPOINT
# ======================================================
def main():
    parser = argparse.ArgumentParser(
        description="Process tracing TXT files without prediction"
    )
    parser.add_argument(
        "--txt_dir",
        required=True,
        help="Directory containing tracing .txt files",
    )
    parser.add_argument(
        "--metadata_csv",
        required=True,
        help="CSV file containing study metadata (must include study_id, ebc)",
    )

    args = parser.parse_args()

    df = pd.read_csv(args.metadata_csv)
    print(df.head())

    required_cols = {"study_id", "ebc"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in metadata CSV: {missing}")

    runner = ManageTracingsNoPred(args.txt_dir, df)
    runner.run()


if __name__ == "__main__":
    main()