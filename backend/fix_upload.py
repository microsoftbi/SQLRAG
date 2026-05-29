
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''        # 保存到数据库
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Documents (Title, Content, Source, Metadata) VALUES (?, ?, ?, ?); SELECT IDENT_CURRENT('Documents') AS DocumentId;",
            (
                file.filename,
                text_content,
                f"上传文件：{file.filename}",
                json.dumps({
                    "filename": file.filename,
                    "filesize": len(file_content),
                    "filetype": file_ext,
                    "upload_time": datetime.now().isoformat()
                })
            ),
        )
        
        # 获取新插入的文档 ID
        row = cursor.fetchone()
        document_id = int(row[0]) if row and row[0] is not None else None
        
        conn.commit()
        
        if document_id is None or document_id == 0:
            raise Exception("Failed to get document ID after insert")
        
        # 立即创建分块
        if text_content:
            create_chunks_from_content(document_id, text_content, conn)
        
        logging.info(f"Document uploaded: {file.filename}, ID: {document_id}")
        
        return JSONResponse(
            status_code=200,
            content={"message": "Document uploaded successfully", "filename": file.filename, "documentId": document_id}
        )'''

new_code = '''        # 保存到数据库
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Documents (Title, Content, Source, Metadata) VALUES (?, ?, ?, ?)",
            (
                file.filename,
                text_content,
                f"上传文件：{file.filename}",
                json.dumps({
                    "filename": file.filename,
                    "filesize": len(file_content),
                    "filetype": file_ext,
                    "upload_time": datetime.now().isoformat()
                })
            ),
        )
        conn.commit()
        
        # 使用单独的查询获取刚插入的文档 ID
        cursor.execute("SELECT IDENT_CURRENT('Documents')")
        row = cursor.fetchone()
        document_id = int(row[0]) if row and row[0] is not None else None
        
        if document_id is None or document_id == 0:
            raise Exception("Failed to get document ID after insert")
        
        # 立即创建分块
        if text_content:
            create_chunks_from_content(document_id, text_content, conn)
        
        logging.info(f"Document uploaded: {file.filename}, ID: {document_id}")
        
        return JSONResponse(
            status_code=200,
            content={"message": "Document uploaded successfully", "filename": file.filename, "documentId": document_id}
        )'''

new_content = content.replace(old_code, new_code)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('File updated successfully')
