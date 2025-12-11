from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.vector import vector_upload, excel_upload
from utils.seaweed import upload_file

def percentage(current, total):
    if total == 0:
        return 0  # Avoid division by zero
    percentage = (current / total) * 100
    return int(percentage)

def content_spliter(doc):
    with open(doc) as f:
        state_of_the_union = f.read()
    
    # print("book \n"*3, state_of_the_union)
    print("book\n"*3)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=70,
        length_function=len,
        is_separator_regex=False,
    )
    
    return text_splitter.create_documents([state_of_the_union])


def document_upload_vector(doc_location: str, doc_name: str, collection_name: str):

    doc_for_upload = str(doc_location).replace("\\", "/")
    file_url = upload_file(doc_for_upload)
    file_type = {"xlsx":"Excel","xls":"Excel","txt":"Text","md":"Markdown","docx":"Word"}.get(doc_for_upload.split('.')[-1].lower(), "Unknown")
    print(file_type)

    if file_type == "Excel":
        x = excel_upload(
            excel_path=doc_location,
            collection_name=collection_name,
            metadata_columns=[file_url],
        )
        return 1

    elif file_type == "Text" or file_type == "Markdown":
        texts = content_spliter(doc_location)
        docs_len = len(texts)
        print(docs_len)
        for i in range(docs_len):
            metadata = {
                # "doccumet": doc_name,
                # "page_number": i+1,
                "document_link": file_url, 
            }

            vector_upload(
                data=texts[i].page_content,
                metadata=metadata,
                collection_name=collection_name
            )
            x = percentage(i+1, docs_len)
            print(f"completed {x}%")
        print(docs_len)
        return 1
    
    else: 

        return "file not supported"
        

