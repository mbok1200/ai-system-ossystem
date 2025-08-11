import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv(".env")

def debug_pinecone():
    """Детальна діагностика Pinecone"""
    
    print("🔧 Перевіряю Pinecone підключення...")
    
    # API ключ
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "streamlit")
    
    print(f"🔑 API Key: {api_key[:20]}..." if api_key else "❌ API Key відсутній")
    print(f"📋 Index Name: {index_name}")
    
    try:
        # Підключення
        pc = Pinecone(api_key=api_key)
        print("✅ Pinecone client створено")
        
        # Список індексів
        indexes = pc.list_indexes()
        available_indexes = [idx.name for idx in indexes]
        print(f"📋 Доступні індекси: {available_indexes}")
        
        if index_name not in available_indexes:
            print(f"❌ Індекс '{index_name}' НЕ ІСНУЄ!")
            return False
        
        # Підключення до індексу
        index = pc.Index(index_name)
        print(f"✅ Підключено до індексу '{index_name}'")
        
        # Статистика
        stats = index.describe_index_stats()
        print(f"📊 Статистика індексу:")
        print(f"   Total vectors: {stats.total_vector_count}")
        print(f"   Dimension: {stats.dimension}")
        print(f"   Namespaces: {dict(stats.namespaces) if stats.namespaces else 'Default'}")
        
        # Тестовий upsert
        print("\n🧪 Тестовий upsert...")
        test_vector = {
            'id': 'test-vector-123',
            'values': [0.1] * stats.dimension,
            'metadata': {'test': 'true', 'timestamp': '2025-07-16'}
        }
        
        response = index.upsert(vectors=[test_vector])
        print(f"📤 Upsert response: {response}")
        
        # Перевіряємо чи додався
        import time
        time.sleep(2)  # Чекаємо індексацію
        
        query_result = index.query(
            vector=[0.1] * stats.dimension,
            top_k=1,
            include_metadata=True
        )
        
        print(f"🔍 Query result: {len(query_result.matches)} matches")
        if query_result.matches:
            match = query_result.matches[0]
            print(f"   ID: {match.id}, Score: {match.score}")
        
        # Видаляємо тестовий вектор
        index.delete(ids=['test-vector-123'])
        print("🗑️ Тестовий вектор видалено")
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False

if __name__ == "__main__":
    debug_pinecone()