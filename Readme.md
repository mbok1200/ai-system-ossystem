ai_system/
├── main.py                    ← запуск інтерфейсу Gradio
├── rag_engine.py              ← пошук у Pinecone (RAG)
├── function_agent.py          ← обробка function-calling
├── tools/
│   ├── google_search.py       ← fallback на пошук у Google
│   └── redmine_api.py         ← інтеграція з Redmine
├── data/
│   └── dataset.jsonl          ← датасет інструкцій
└── docs/
    └── README.md              ← документація
# .env
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENV=your_pinecone_env
PINECONE_INDEX_NAME=your_index_name

# Опціонально
REDMINE_URL=https://your-redmine.com
REDMINE_API_KEY=your_redmine_key
REDMINE_USER_ID=123
GOOGLE_API_KEY=your_google_key
GOOGLE_SEARCH_ENGINE_ID=your_search_id


# Перевірити стан індексу
python upload_docs.py --check

# Завантажити один файл
python upload_docs.py --file "/path/to/document.pdf"

# Завантажити всі файли з директорії
python upload_docs.py --directory "/path/to/docs" --recursive

# Очистити індекс (обережно!)
python upload_docs.py --clear