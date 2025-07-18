from __future__ import annotations
# -*- coding: utf-8 -*-
# code generated by Prisma. DO NOT EDIT.
# fmt: off
# -- template metadata.py.jinja --


PRISMA_MODELS: set[str] = {
    'KnowledgeBase',
    'Usuario',
    'Sessao',
    'FluxoConversa',
    'Mensagem',
    'SlotPreenchido',
}

RELATIONAL_FIELD_MAPPINGS: dict[str, dict[str, str]] = {
    'KnowledgeBase': {
    },
    'Usuario': {
        'sessoes': 'Sessao',
    },
    'Sessao': {
        'usuario': 'Usuario',
        'mensagens': 'Mensagem',
        'fluxo': 'FluxoConversa',
    },
    'FluxoConversa': {
        'sessao': 'Sessao',
        'slots': 'SlotPreenchido',
    },
    'Mensagem': {
        'sessao': 'Sessao',
    },
    'SlotPreenchido': {
        'fluxo': 'FluxoConversa',
    },
}

# fmt: on