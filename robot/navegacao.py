"""Decisao de percurso pela regra da mao direita, sem acesso ao hardware.

Chame decidir_movimento em um ponto de decisao do labirinto, com o robo
alinhado e as tres leituras referentes a mesma posicao. A prioridade e:
direita, frente, esquerda e meia-volta.

O chamador deve executar cada manobra por completo antes de decidir de novo.
A funcao nao controla os motores, nao centraliza o robo no corredor e nao
detecta a saida. Tres lados livres tambem podem representar um cruzamento.
Em labirintos com ciclos, esta estrategia pode repetir o mesmo percurso.
"""


ANDAR = "ANDAR"
VIRAR_DIREITA = "VIRAR_DIREITA"
VIRAR_ESQUERDA = "VIRAR_ESQUERDA"
MEIA_VOLTA = "MEIA_VOLTA"
PARAR = "PARAR"


def _distancia_valida(valor):
    # Rejeita leitura ausente, zero, negativa, NaN e infinito.
    return (
        isinstance(valor, (int, float))
        and not isinstance(valor, bool)
        and 0 < valor < float("inf")
    )


def decidir_movimento(frente_mm, esquerda_mm, direita_mm, limite_mm=150):
    """Retorna uma acao a partir das distancias em milimetros.

    Distancia <= limite_mm representa uma parede, como no teste funcional.
    O limite padrao e 150 mm e deve ser calibrado para a geometria do robo
    e do labirinto, especialmente para distinguir aberturas nas laterais.

    Qualquer leitura invalida retorna PARAR. Excecoes na leitura dos
    sensores devem ser tratadas pelo chamador, que tambem deve parar o robo.
    Um limite invalido gera ValueError por ser um erro de configuracao.

    As acoes sao relativas a orientacao atual:
    - VIRAR_DIREITA: girar 90 graus e avancar pela passagem escolhida.
    - ANDAR: avancar ate o proximo ponto de decisao.
    - VIRAR_ESQUERDA: girar 90 graus e avancar pela passagem escolhida.
    - MEIA_VOLTA: girar 180 graus e retornar pelo caminho anterior.
    - PARAR: desligar os motores e obter novas leituras validas.

    A meia-volta pressupoe que o caminho de onde o robo veio esta livre;
    os tres sensores nao medem a parte de tras.

    Exemplo de chamada, sem executar movimento:
        acao = decidir_movimento(
            frente_mm=300, esquerda_mm=80, direita_mm=250
        )
        # acao == VIRAR_DIREITA
    """
    if not _distancia_valida(limite_mm):
        raise ValueError("limite_mm deve ser um numero positivo e finito")

    for distancia in (frente_mm, esquerda_mm, direita_mm):
        if not _distancia_valida(distancia):
            return PARAR

    if direita_mm > limite_mm:
        return VIRAR_DIREITA
    if frente_mm > limite_mm:
        return ANDAR
    if esquerda_mm > limite_mm:
        return VIRAR_ESQUERDA
    return MEIA_VOLTA
