# tests/test_semantic.py
# Usa o lexer.py e parser_.py

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lexer import Lexer
from parser_ import Parser
from semantic_analyzer import AnalisadorSemantico, SemanticError


def analisar(codigo):
    """Helper: lexer -> parser -> analisador semântico."""
    tokens   = Lexer(codigo).tokenize()
    ast      = Parser(tokens).parse()
    analisador = AnalisadorSemantico()
    analisador.analisar(ast)
    return analisador


class TestTabelaDeSimbolos(unittest.TestCase):

    def test_declaracao_int_valida(self):
        # int x = 10;  deve passar sem erro
        analisador = analisar("int x = 10;")
        simbolo = analisador.tabela.buscar('x')
        self.assertIsNotNone(simbolo)
        self.assertEqual(simbolo.tipo, 'int')

    def test_declaracao_sem_valor_inicial(self):
        # int x;  deve passar sem erro
        analisador = analisar("int x;")
        self.assertIsNotNone(analisador.tabela.buscar('x'))

    def test_declaracao_bool_valida(self):
        analisador = analisar("bool b;")
        self.assertEqual(analisador.tabela.buscar('b').tipo, 'bool')

    def test_redeclaracao_mesmo_escopo_lanca_erro(self):
        with self.assertRaises(SemanticError):
            analisar("int x = 1; int x = 2;")

    def test_variavel_some_ao_fechar_bloco(self):
        # Declara x dentro do if, depois tenta usar fora

        # (Atribuicao ainda não está no parser, então testamos via busca direta)
        codigo = "if (1 < 2) { int x = 5; }"
        analisador = analisar(codigo)
        # Após analisar, o escopo do bloco foi fechado -> x não deve existir no escopo global
        self.assertIsNone(analisador.tabela.buscar('x'))


class TestVerificacaoDeTipos(unittest.TestCase):

    def test_soma_int_valida(self):
        # int r = 2 + 3;   ok
        analisar("int r = 2 + 3;")

    def test_tipo_incompativel_na_declaracao(self):
        # int x = 1 < 2;   expressão é bool, tipo declarado é int -> ERRO
        with self.assertRaises(SemanticError):
            analisar("int x = 1 < 2;")

    def test_comparacao_retorna_bool(self):
        # bool b = 1 < 2;  ok
        analisar("bool b = 1 < 2;")

    def test_bool_declarado_com_int_lanca_erro(self):
        # bool b = 5 + 3; expressão é int, tipo é bool = ERRO
        with self.assertRaises(SemanticError):
            analisar("bool b = 5 + 3;")

    def test_operacao_com_variavel_valida(self):
        # int x = 10; int y = x + 5;  ok
        analisar("int x = 10; int y = x + 5;")

    def test_variavel_nao_declarada_lanca_erro(self):
        # int y = z + 1;   z não declarada = ERRO
        with self.assertRaises(SemanticError):
            analisar("int y = z + 1;")

    def test_multiplas_declaracoes_validas(self):
        analisar("int a = 1; int b = 2; int c = a + b;")

    def test_expressao_comparacao_encadeada(self):
        # bool r = 1 + 2 < 4;   ok (int < int bool)
        analisar("bool r = 1 + 2 < 4;")


class TestComandoIf(unittest.TestCase):

    def test_if_com_condicao_bool(self):
        # if (1 < 2) { int x = 1; }  = ok
        analisar("if (1 < 2) { int x = 1; }")

    def test_if_with_int_condition_raises_error(self):
        # if (1 + 1) { ... } condição é int, deve ser bool  ERRO
        with self.assertRaises(SemanticError):
            analisar("if (1 + 1) { int x = 1; }")

    def test_if_else(self):
        # if (1 < 2) { int a = 1; } else { int b = 2; }   ok
        analisar("if (1 < 2) { int a = 1; } else { int b = 2; }")

    def test_variavel_do_bloco_nao_vaza_para_fora(self):
        # x declarado no bloco then não deve existir no escopo externo
        codigo = "if (1 < 2) { int x = 99; }"
        analisador = analisar(codigo)
        self.assertIsNone(analisador.tabela.buscar('x'))

    def test_variavel_global_acessivel_dentro_do_bloco(self):
        # int n = 10;  if (n < 20) { int r = n + 1; }  ok
        analisar("int n = 10; if (n < 20) { int r = n + 1; }")

    def test_if_aninhado(self):
        analisar("if (1 < 2) { if (3 < 4) { int x = 0; } }")


if __name__ == '__main__':
    unittest.main()
