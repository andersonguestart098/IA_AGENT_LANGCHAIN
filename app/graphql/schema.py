# app/graphql/schema.py

import strawberry
from typing import List, Optional
from app.generated.client import Prisma

# 🔹 Tipos GraphQL
@strawberry.type
class Slot:
    nome: str
    valor: str

@strawberry.type
class Fluxo:
    id: int
    etapa: str
    intencao: str
    pedido: str
    resposta: str
    slots: List[Slot]

# 🔹 Query
@strawberry.type
class Query:
    @strawberry.field
    async def fluxo_por_id(self, id: int) -> Optional[Fluxo]:
        prisma = Prisma()
        await prisma.connect()
        fluxo = await prisma.fluxoconversa.find_unique(
    where={"id": id},
    include={"slots": True}
)

        await prisma.disconnect()

        if not fluxo:
            return None

        return Fluxo(
            id=fluxo.id,
            etapa=fluxo.etapa,
            intencao=fluxo.intencao,
            pedido=fluxo.pedido,
            resposta=fluxo.resposta,
            slots=[Slot(nome=s.nome, valor=s.valor) for s in fluxo.slots]

        )
