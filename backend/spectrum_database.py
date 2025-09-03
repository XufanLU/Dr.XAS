# connect with Material data repository 
# 
# [https://mdr.nims.go.jp/api/v1/datasets?q=XAFS specimen:"Nickel"](https://mdr.nims.go.jp/api/v1/datasets?q=XAFS%20specimen:%22Nickel%22) instead of nickel, could have a lot 



import requests



def get_datasets():
    response = requests.get("https://mdr.nims.go.jp/api/v1/datasets?q=XAFS")

    datasets_list=response.json()
    datasets_map = {}
    count = 0

    for i in datasets_list:
        if len(i['data']['attributes']['specimens'])>=1:
            datasets_map[i['data']['attributes']['titles'][0]['title']] = (i['data']['id'], i['data']['attributes']['specimens'][0]['name'])
        else:
            datasets_map[i['data']['attributes']['titles'][0]['title']] = (i['data']['id'], '')
        count += 1

    print(datasets_map)
    print(count)

    return datasets_map



if __name__ == "__main__":
    datasets = get_datasets()
    print(datasets)