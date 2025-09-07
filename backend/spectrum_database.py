# connect with Material data repository
#
# [https://mdr.nims.go.jp/api/v1/datasets?q=XAFS specimen:"Nickel"](https://mdr.nims.go.jp/api/v1/datasets?q=XAFS%20specimen:%22Nickel%22) instead of nickel, could have a lot


import requests
import zipfile
import os


def get_datasets():
    response = requests.get("https://mdr.nims.go.jp/api/v1/datasets?q=XAFS")

    datasets_list = response.json()
    datasets_map = {}
    count = 0

    for i in datasets_list:
        if len(i["data"]["attributes"]["specimens"]) >= 1:
            datasets_map[i["data"]["attributes"]["titles"][0]["title"]] = (
                i["data"]["id"],
                i["data"]["attributes"]["specimens"][0]["name"],
            )
        else:
            datasets_map[i["data"]["attributes"]["titles"][0]["title"]] = (
                i["data"]["id"],
                "",
            )
        count += 1

    print(datasets_map)
    print(count)

    return datasets_map


def get_data_by_id(dataset_id):
    url = f"https://mdr.nims.go.jp/datasets/{dataset_id}.zip"
    response = requests.get(url)
    if response.status_code == 200:
        zip_path = f"{dataset_id}.zip"
        parent_dir = os.path.dirname(os.path.abspath(__file__))
        sub_folder = os.path.join(parent_dir, "online_xas_data")
        sub_sub_folder = os.path.join(sub_folder, dataset_id)

        os.makedirs(sub_folder, exist_ok=True)
        os.makedirs(sub_sub_folder, exist_ok=True)
        zip_file_path = os.path.join(sub_sub_folder, zip_path)
        with open(zip_file_path, "wb") as f:
            f.write(response.content)
        txt_files = []
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(
                sub_sub_folder
            )  # extract to sub folder in parent directory
            for file in zip_ref.namelist():
                if file.endswith(".txt"):
                    txt_files.append(
                        os.path.abspath(os.path.join(sub_sub_folder, file))
                    )
        return txt_files


if __name__ == "__main__":
    datasets = get_datasets()
    print(datasets)
    result = get_data_by_id(
        "ff693629-a57c-4475-aaa8-5a4a815db425"
    )  # example dataset id
    print(result)
