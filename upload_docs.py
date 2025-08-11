#!/usr/bin/env python3
import argparse
import sys
import os
import logging
from pathlib import Path

from document_loader import DocumentLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    parser = argparse.ArgumentParser(description="Завантаження документів в Pinecone")
    parser.add_argument('--file', help='Завантажити один файл')
    parser.add_argument('--directory', help='Завантажити всі файли з директорії')
    parser.add_argument('--recursive', action='store_true', help='Рекурсивний пошук в підпапках')
    parser.add_argument('--check', action='store_true', help='Перевірити стан індексу')
    
    args = parser.parse_args()
    
    try:
        # Ініціалізація з автоматичним створенням індексу
        loader = DocumentLoader("streamlit", auto_create_index=True, dimension=768)
        
        # Перевірка індексу
        if args.check:
            print("🔍 Перевіряю стан індексу...")
            status = loader.check_index_status()
            
            print(f"📊 Індекс 'streamlit':")
            print(f"   Існує: {status['exists']}")
            print(f"   Векторів: {status.get('total_vectors', 0)}")
            print(f"   Розмірність: {status.get('dimension', 'N/A')}")
            print(f"   Порожній: {status['is_empty']}")
            
            if status.get('namespaces'):
                print(f"   Namespaces:")
                for ns, data in status['namespaces'].items():
                    ns_name = f"'{ns}'" if ns else "'(порожній)'"
                    print(f"      {ns_name}: {data['vector_count']} векторів")
            
            return
        
        # Завантаження файлу
        if args.file:
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"❌ Файл не існує: {file_path}")
                return
            
            print(f"📄 Завантажую файл: {file_path.name}")
            result = loader.load_file(file_path)
            
            if result['success']:
                print(f"✅ Успішно завантажено: {result['chunks_created']} чанків, {result['vectors_uploaded']} векторів")
            else:
                print(f"❌ Помилка: {result['error']}")
            return
        
        # Завантаження директорії
        if args.directory:
            print(f"📁 Завантажую директорію: {args.directory}")
            result = loader.load_directory(args.directory, recursive=args.recursive)
            
            if result['success']:
                print(f"✅ Завершено: {result['successful']}/{result['total_files']} файлів успішно")
            else:
                print(f"❌ Помилка: {result['error']}")
            return
        
        # Якщо нічого не вказано
        print("❓ Вкажіть --file, --directory або --check")
        parser.print_help()
        
    except Exception as e:
        logging.error(f"❌ Критична помилка: {e}")
        print(f"💥 Помилка: {e}")

if __name__ == "__main__":
    main()