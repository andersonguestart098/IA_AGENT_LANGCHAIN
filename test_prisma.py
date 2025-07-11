# test_prisma.py
import asyncio
from app.generated.client import Prisma

async def main():
    db = Prisma()
    await db.connect()

    # Testa se consegue buscar da tabela KnowledgeBase
    registros = await db.knowledgebase.find_many()
    print("Registros encontrados:", registros)

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
