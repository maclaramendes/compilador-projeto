# semantic_analyzer.py

# Compatível com o parser_.py do projeto (nós: Programa, DeclaracaoVariavel,
# Atribuicao, OperacaoBinaria, Numero, Identificador, Bloco, ComandoIf)


class SemanticError(Exception):
    pass



class Simbolo:
    """Representa uma variável registrada na tabela de símbolos."""
    def __init__(self, nome, tipo, nivel_escopo):
        self.nome         = nome
        self.tipo         = tipo          # 'int', 'bool', 'string'
        self.nivel_escopo = nivel_escopo

    def __repr__(self):
        return f"Simbolo(nome={self.nome!r}, tipo={self.tipo!r}, escopo={self.nivel_escopo})"


class TabelaDeSimbolos:
    """
    Pilha de escopos.
    - Cada escopo é um dicionário nome -> Simbolo.
    - Ao entrar num bloco { } abrimos um novo escopo (enter_escopo).
    - Ao sair do bloco } fechamos (sair_escopo) e as variáveis somem.
    """

    def __init__(self):
        self.escopos = [{}]   # começa com o escopo global

    @property
    def nivel_atual(self):
        return len(self.escopos) - 1

    def entrar_escopo(self):
        self.escopos.append({})

    def sair_escopo(self):
        if len(self.escopos) == 1:
            raise RuntimeError("Erro interno: tentativa de fechar o escopo global.")
        self.escopos.pop()

    def declarar(self, nome, tipo):
        """
        Registra a variável no escopo atual.
        Lança SemanticError se já estiver declarada neste mesmo escopo.
        """
        escopo_atual = self.escopos[-1]
        if nome in escopo_atual:
            raise SemanticError(
                f"Variável '{nome}' já foi declarada neste escopo."
            )
        escopo_atual[nome] = Simbolo(nome, tipo, self.nivel_atual)

    def buscar(self, nome):
        """
        Busca do escopo mais interno para o mais externo.
        Retorna o Simbolo ou None se não encontrar.
        """
        for escopo in reversed(self.escopos):
            if nome in escopo:
                return escopo[nome]
        return None

    def buscar_ou_erro(self, nome):
        """Igual a buscar, mas lança SemanticError se não encontrar."""
        simbolo = self.buscar(nome)
        if simbolo is None:
            raise SemanticError(
                f"Variável '{nome}' usada antes de ser declarada."
            )
        return simbolo


# Mapeamento (tipo_esq, operador_no_token, tipo_dir) -> tipo_resultado.
# O operador vem do token: token.type ('MAIS', 'MENOR', etc.)

REGRAS_BINARIAS = {
    # Aritméticas (int op int -> int)
    ('int', 'MAIS',   'int'): 'int',
    ('int', 'MENOS',  'int'): 'int',
    ('int', 'MULT',   'int'): 'int',
    ('int', 'DIV',    'int'): 'int',

    # Comparações (int op int -> bool)
    ('int', 'MENOR',        'int'): 'bool',
    ('int', 'MAIOR',        'int'): 'bool',
    ('int', 'MENOR_IGUAL',  'int'): 'bool',
    ('int', 'MAIOR_IGUAL',  'int'): 'bool',
    ('int', 'IGUAL_COMP',   'int'): 'bool',
    ('int', 'DIFERENTE',    'int'): 'bool',

    # Comparações (bool op bool -> bool)
    ('bool', 'IGUAL_COMP',  'bool'): 'bool',
    ('bool', 'DIFERENTE',   'bool'): 'bool',
}


def verificar_operacao_binaria(tipo_esq, op_type, tipo_dir):
    """
    Retorna o tipo resultado da operação ou lança SemanticError.
    op_type é o token.type do operador ('MAIS', 'MENOR_IGUAL', etc.)
    """
    resultado = REGRAS_BINARIAS.get((tipo_esq, op_type, tipo_dir))
    if resultado is None:
        # Converte token.type para símbolo legível no erro
        simbolo_op = {
            'MAIS': '+', 'MENOS': '-', 'MULT': '*', 'DIV': '/',
            'MENOR': '<', 'MAIOR': '>', 'MENOR_IGUAL': '<=',
            'MAIOR_IGUAL': '>=', 'IGUAL_COMP': '==', 'DIFERENTE': '!=',
        }.get(op_type, op_type)
        raise SemanticError(
            f"Operação inválida: '{tipo_esq}' {simbolo_op} '{tipo_dir}' não é permitida."
        )
    return resultado


class AnalisadorSemantico:
    """
    Percorre a AST e verifica regras semânticas.
    Usa os mesmos nomes de nó do parser_.py do projeto:
      Programa, DeclaracaoVariavel, Atribuicao, OperacaoBinaria,
      Numero, Identificador, Bloco, ComandoIf
    """

    def __init__(self):
        self.tabela = TabelaDeSimbolos()

    def analisar(self, ast):
        """Ponto de entrada. Recebe o nó Programa e analisa tudo."""
        self.visitar(ast)

    # --- Despacho ---

    def visitar(self, no):
        nome_metodo = f'visitar_{type(no).__name__}'
        metodo = getattr(self, nome_metodo, self.visita_generica)
        return metodo(no)

    def visita_generica(self, no):
        raise NotImplementedError(
            f"AnalisadorSemantico: sem método 'visitar_{type(no).__name__}'. "
            f"Adicione-o caso queira suportar este nó."
        )

    # --- Nós do programa ---

    def visitar_Programa(self, no):
        for stmt in no.declaracoes:
            self.visitar(stmt)

    def visitar_DeclaracaoVariavel(self, no):
        """
        int x = expr;   ou   bool b;
        no.tipo            -> Token do tipo ('INT', 'BOOL')
        no.nome_variavel   -> nó Identificador
        no.expressao       -> nó da expressão ou None
        """
        tipo_declarado = no.tipo.type.lower()   # 'INT' -> 'int', 'BOOL' -> 'bool'

        if no.expressao is not None:
            tipo_expr = self.visitar(no.expressao)
            if tipo_expr != tipo_declarado:
                raise SemanticError(
                    f"Tipo incompatível ao declarar '{no.nome_variavel.nome}': "
                    f"esperado '{tipo_declarado}', mas a expressão é '{tipo_expr}'."
                )

        # Registra depois de visitar a expressão (evita `int x = x + 1`)
        self.tabela.declarar(no.nome_variavel.nome, tipo_declarado)

    def visitar_Atribuicao(self, no):
        """
        x = expr;
        no.nome_variavel -> nó Identificador
        no.expressao     -> nó da expressão
        """
        simbolo   = self.tabela.buscar_ou_erro(no.nome_variavel.nome)
        tipo_expr = self.visitar(no.expressao)
        if tipo_expr != simbolo.tipo:
            raise SemanticError(
                f"Tipo incompatível ao atribuir a '{no.nome_variavel.nome}': "
                f"variável é '{simbolo.tipo}', expressão é '{tipo_expr}'."
            )

    def visitar_ComandoIf(self, no):
        """
        if (cond) bloco_then [else bloco_else]
        no.condicao    -> expressão booleana
        no.bloco_then  -> nó Bloco
        no.bloco_else  -> nó Bloco ou None
        """
        tipo_cond = self.visitar(no.condicao)
        if tipo_cond != 'bool':
            raise SemanticError(
                f"A condição do 'if' deve ser booleana, mas é '{tipo_cond}'."
            )
        self.visitar(no.bloco_then)
        if no.bloco_else is not None:
            self.visitar(no.bloco_else)

    def visitar_Bloco(self, no):
        """
        { stmt* }
        Bloco abre e fecha seu próprio escopo.
        no.declaracoes -> lista de statements
        """
        self.tabela.entrar_escopo()
        for stmt in no.declaracoes:
            self.visitar(stmt)
        self.tabela.sair_escopo()

    # --- Expressões (retornam o tipo inferido) ---

    def visitar_OperacaoBinaria(self, no):
        """
        no.esquerda -> nó expressão
        no.op       -> Token do operador (usamos no.op.type)
        no.direita  -> nó expressão
        """
        tipo_esq = self.visitar(no.esquerda)
        tipo_dir = self.visitar(no.direita)
        return verificar_operacao_binaria(tipo_esq, no.op.type, tipo_dir)

    def visitar_Numero(self, no):
        return 'int'

    def visitar_Identificador(self, no):
        simbolo = self.tabela.buscar_ou_erro(no.nome)
        return simbolo.tipo