from uuid import uuid4
import requests
import os

from bs4 import BeautifulSoup
from urllib.parse import unquote

# from . import get_new_name

image_db = os.getenv("RAILWAY_SEAWEED_DB")


# # def image_uplode(image_path: str, title: str, foulder: str):
# def image_uplode(image_path: str, title: str = None):

#     imgs = get_all_images()
#     _count, name = get_new_name(new_file=image_path, names_list=imgs)
#     print(name)

#     # url = f"{image_db}/{foulder}/{name}"
#     url = f"{image_db}/mybucket/{name}"

#     with open(image_path, "rb") as f:
#         res = (requests.post(url, files={"file": f})).json()

#     print(res)
#     # out = f"{url}{res["name"]}"
#     print("✅ File uploaded to SeaweedFS on URL:", url)

#     return url


def upload_file(file_path: str):
    filename = file_path.split("/")[-1]

    upload_url = f"{image_db}/{file_path}"

    with open(file_path, "rb") as f:
        files = {"file": (filename, f)}
        resp = requests.post(upload_url, files=files)

    resp.raise_for_status()

    print("✅ Upload success")
    print("File URL:", upload_url)
    return upload_url


def image_download(image_url: str):

    # data = requests.get(image_url).content
    # with open('downloaded.jpg', 'wb') as f:
    #     f.write(data)
    # return data

    download = requests.get(image_url)
    open('downloaded.jpg', 'wb').write(download.content)
    print("✅ File downloaded from SeaweedFS")
    return download


def image_delete(image_url: str):

    delete = requests.delete(image_url)
    print("✅ File deleted from SeaweedFS")
    return delete


# def get_all_images(base_url: str, folder: str):
def get_all_images():
    '''
    This function return all files in that foulder
    '''
    url = f"{image_db}/mybucket/?list"

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    files = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("/mybucket/") and not href.endswith("/"):
            filename = unquote(href.split("/")[-1])  # decode %20 etc.
            files.append(filename)

    print("✅ Files in folder:")
    # print(files)
    return files

