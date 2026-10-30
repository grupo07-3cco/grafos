"""
Grafo de geolocalização da UTI Neonatal.

Monta um grafo (NetworkX) com a posição física de cada elemento da UTI:
servidor, gateway, incubadoras, pulseiras e sensores. As arestas representam
as conexões de dados e têm como peso a distância em metros entre os nós.

Uso:
    python grafo_uti.py
Saída:
    grafo_uti.png + relatório no terminal
"""

import math
import random

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

SEED = 42
ARQUIVO_SAIDA = "grafo_uti.png"

# Dimensões da planta da UTI (metros)
LARGURA_UTI = 20
ALTURA_UTI = 12

# Faixas de referência de cada sensor:
# (mínimo normal, máximo normal, tolerância para "alerta", unidade)
FAIXAS = {
    "umidade":     (50.0, 65.0, 5.0, "%"),     # umidade do ar da incubadora
    "temp_inc":    (32.0, 34.0, 0.5, "°C"),    # temperatura do ar da incubadora
    "ruido":       (0.0, 45.0, 10.0, "dB"),    # ruído dentro da incubadora
    "temp_bebe":   (36.5, 37.5, 0.5, "°C"),    # temperatura corporal (pulseira)
    "oxigenio":    (95.0, 100.0, 5.0, "%"),    # SpO2 (pulseira)
    "batimento":   (120.0, 160.0, 20.0, "bpm"),  # frequência cardíaca (pulseira)
}

SENSORES_INCUBADORA = ["umidade", "temp_inc", "ruido"]
SENSORES_PULSEIRA = ["temp_bebe", "oxigenio", "batimento"]

ROTULOS = {
    "umidade": "U", "temp_inc": "T", "ruido": "R",
    "temp_bebe": "T°", "oxigenio": "O₂", "batimento": "FC",
}

CORES_STATUS = {"normal": "#2e9e44", "alerta": "#f0a500", "critico": "#d62728"}
PRIORIDADE_STATUS = {"normal": 0, "alerta": 1, "critico": 2}


def classificar(sensor, valor):
    """Retorna 'normal', 'alerta' ou 'critico' conforme a faixa do sensor."""
    minimo, maximo, tolerancia, _ = FAIXAS[sensor]
    if minimo <= valor <= maximo:
        return "normal"
    if minimo - tolerancia <= valor <= maximo + tolerancia:
        return "alerta"
    return "critico"


def simular_leitura(sensor, rng):
    """Gera uma leitura simulada: na maioria das vezes normal, às vezes fora da faixa."""
    minimo, maximo, tolerancia, _ = FAIXAS[sensor]
    sorteio = rng.random()
    if sorteio < 0.80:
        valor = rng.uniform(minimo, maximo)
    elif sorteio < 0.93:
        valor = rng.choice([minimo - tolerancia / 2, maximo + tolerancia / 2])
    else:
        valor = rng.choice([minimo - tolerancia * 2, maximo + tolerancia * 2])
    return round(valor, 1)


def pior_status(statuses):
    return max(statuses, key=PRIORIDADE_STATUS.get)


def distancia(pos_a, pos_b):
    return round(math.dist(pos_a, pos_b), 2)


def montar_grafo():
    rng = random.Random(SEED)
    G = nx.Graph()

    # Infraestrutura fixa
    G.add_node("Servidor", tipo="servidor", pos=(18.8, 6.0))
    G.add_node("Gateway", tipo="gateway", pos=(10.0, 6.0))
    G.add_edge("Servidor", "Gateway", conexao="cabo")

    # Incubadoras em duas fileiras (posição x, y em metros na planta)
    posicoes_incubadoras = [
        (4.5, 9.0), (10.0, 9.0), (15.5, 9.0),
        (4.5, 3.0), (10.0, 3.0), (15.5, 3.0),
    ]

    for i, (x, y) in enumerate(posicoes_incubadoras, start=1):
        incubadora = f"INC-{i:02d}"
        pulseira = f"PUL-{i:02d}"

        G.add_node(incubadora, tipo="incubadora", pos=(x, y))
        G.add_edge(incubadora, "Gateway", conexao="wifi")

        # A pulseira fica no neonato, dentro da incubadora
        G.add_node(pulseira, tipo="pulseira", pos=(x + 1.6, y))
        G.add_edge(pulseira, incubadora, conexao="bluetooth")

        # Sensores fixos na incubadora (à esquerda / acima / abaixo dela)
        deslocamentos_inc = [(-1.4, 0.9), (-1.4, 0.0), (-1.4, -0.9)]
        for sensor, (dx, dy) in zip(SENSORES_INCUBADORA, deslocamentos_inc):
            adicionar_sensor(G, rng, incubadora, sensor, (x + dx, y + dy))

        # Sensores da pulseira (em volta da pulseira)
        deslocamentos_pul = [(0.9, 0.9), (1.1, 0.0), (0.9, -0.9)]
        px, py = G.nodes[pulseira]["pos"]
        for sensor, (dx, dy) in zip(SENSORES_PULSEIRA, deslocamentos_pul):
            adicionar_sensor(G, rng, pulseira, sensor, (px + dx, py + dy))

    # Status dos dispositivos = pior status entre os seus sensores
    for no, dados in G.nodes(data=True):
        if dados["tipo"] in ("incubadora", "pulseira"):
            sensores = [v for v in G.neighbors(no) if G.nodes[v]["tipo"] == "sensor"]
            dados["status"] = pior_status(G.nodes[s]["status"] for s in sensores)

    # Peso das arestas = distância física (metros)
    for a, b in G.edges:
        G.edges[a, b]["peso"] = distancia(G.nodes[a]["pos"], G.nodes[b]["pos"])

    return G


def adicionar_sensor(G, rng, dispositivo, sensor, pos):
    valor = simular_leitura(sensor, rng)
    no = f"{dispositivo}/{sensor}"
    G.add_node(
        no,
        tipo="sensor",
        sensor=sensor,
        dispositivo=dispositivo,
        valor=valor,
        unidade=FAIXAS[sensor][3],
        status=classificar(sensor, valor),
        pos=pos,
    )
    G.add_edge(no, dispositivo, conexao="interna")


def incubadoras_do(G):
    return [n for n, d in G.nodes(data=True) if d["tipo"] == "incubadora"]


def imprimir_relatorio(G):
    print("=" * 60)
    print("RELATÓRIO DO GRAFO - UTI NEONATAL")
    print("=" * 60)
    print(f"Nós: {G.number_of_nodes()} | Arestas: {G.number_of_edges()}")
    print(f"Grafo conexo (todos os sensores chegam ao servidor)? {nx.is_connected(G)}")

    # Mariana (enfermeira): quais sensores estão fora da faixa agora
    print("\n[Mariana - Enfermagem] Leituras fora da faixa:")
    alertas = [
        (n, d) for n, d in G.nodes(data=True)
        if d["tipo"] == "sensor" and d["status"] != "normal"
    ]
    for no, d in sorted(alertas, key=lambda item: -PRIORIDADE_STATUS[item[1]["status"]]):
        print(f"  {d['status'].upper():8} {no:22} {d['valor']} {d['unidade']}")
    if not alertas:
        print("  Nenhum alerta.")

    # Dr. Rafael (neonatologista): neonato x incubadora lado a lado
    print("\n[Dr. Rafael - Neonatologia] Neonato x incubadora:")
    for no, d in G.nodes(data=True):
        if d["tipo"] != "incubadora":
            continue
        pulseira = no.replace("INC", "PUL")
        leituras_inc = ", ".join(
            f"{ROTULOS[s]}={G.nodes[f'{no}/{s}']['valor']}" for s in SENSORES_INCUBADORA
        )
        leituras_bebe = ", ".join(
            f"{ROTULOS[s]}={G.nodes[f'{pulseira}/{s}']['valor']}" for s in SENSORES_PULSEIRA
        )
        print(f"  {no}: [{leituras_inc}]  <->  {pulseira}: [{leituras_bebe}]")

    # Alice (gestora): infraestrutura, distância até o servidor e grau dos nós
    print("\n[Alice - Gestão] Infraestrutura:")
    for no, d in G.nodes(data=True):
        if d["tipo"] != "incubadora":
            continue
        caminho = nx.shortest_path(G, no, "Servidor", weight="peso")
        metros = nx.shortest_path_length(G, no, "Servidor", weight="peso")
        print(f"  {no} status={d['status']:8} até o servidor: {metros:5.2f} m  "
              f"({' -> '.join(caminho)})")
    print(f"  Grau do Gateway (dispositivos conectados): {G.degree('Gateway') - 1}")
    if "Gateway" in set(nx.articulation_points(G)):
        sem_gateway = G.copy()
        sem_gateway.remove_node("Gateway")
        isoladas = [n for n in incubadoras_do(G) if not nx.has_path(sem_gateway, n, "Servidor")]
        print(f"  Gateway é ponto único de falha: se cair, {len(isoladas)} incubadoras "
              f"ficam sem comunicação com o servidor.")
    print("=" * 60)


def desenhar_grafo(G):
    pos = nx.get_node_attributes(G, "pos")
    fig, ax = plt.subplots(figsize=(14, 9))

    # Planta da UTI
    ax.add_patch(plt.Rectangle((0, 0), LARGURA_UTI, ALTURA_UTI,
                               fill=False, linewidth=2, edgecolor="#555555"))
    ax.text(0.3, ALTURA_UTI - 0.5, "UTI Neonatal - planta (m)", fontsize=10, color="#555555")

    # Arestas por tipo de conexão
    estilos = {
        "cabo":      dict(style="solid", width=3.0, edge_color="#333333"),
        "wifi":      dict(style="dotted", width=1.8, edge_color="#1f77b4"),
        "bluetooth": dict(style="dashed", width=1.5, edge_color="#9467bd"),
        "interna":   dict(style="solid", width=0.8, edge_color="#bbbbbb"),
    }
    for conexao, estilo in estilos.items():
        arestas = [(a, b) for a, b, d in G.edges(data=True) if d["conexao"] == conexao]
        nx.draw_networkx_edges(G, pos, edgelist=arestas, ax=ax, **estilo)

    # Peso (distância) nas arestas Wi-Fi e cabo
    rotulos_arestas = {
        (a, b): f"{d['peso']} m" for a, b, d in G.edges(data=True)
        if d["conexao"] in ("wifi", "cabo")
    }
    nx.draw_networkx_edge_labels(G, pos, edge_labels=rotulos_arestas, ax=ax,
                                 font_size=7, font_color="#1f77b4")

    # Nós: todos em círculo; o tamanho indica o tipo e a cor indica o status
    def nos_do_tipo(tipo):
        return [n for n, d in G.nodes(data=True) if d["tipo"] == tipo]

    def cores(nos):
        return [CORES_STATUS.get(G.nodes[n].get("status"), "#444444") for n in nos]

    nx.draw_networkx_nodes(G, pos, nodelist=nos_do_tipo("servidor"), node_shape="o",
                           node_size=1900, node_color="#444444", ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=nos_do_tipo("gateway"), node_shape="o",
                           node_size=1800, node_color="#1f77b4", ax=ax)
    incubadoras = nos_do_tipo("incubadora")
    nx.draw_networkx_nodes(G, pos, nodelist=incubadoras, node_shape="o", node_size=1500,
                           node_color=cores(incubadoras), edgecolors="black", ax=ax)
    pulseiras = nos_do_tipo("pulseira")
    nx.draw_networkx_nodes(G, pos, nodelist=pulseiras, node_shape="o", node_size=650,
                           node_color=cores(pulseiras), edgecolors="black", ax=ax)
    sensores = nos_do_tipo("sensor")
    nx.draw_networkx_nodes(G, pos, nodelist=sensores, node_shape="o", node_size=260,
                           node_color=cores(sensores), ax=ax)

    # Rótulos
    rotulos = {n: n for n in incubadoras + ["Servidor", "Gateway"]}
    nx.draw_networkx_labels(G, pos, labels=rotulos, font_size=7, font_color="white",
                            font_weight="bold", ax=ax)
    rotulos_pulseiras = {n: n.replace("-", "\n") for n in pulseiras}
    nx.draw_networkx_labels(G, pos, labels=rotulos_pulseiras, font_size=6, font_color="white",
                            font_weight="bold", ax=ax)
    rotulos_sensores = {n: ROTULOS[G.nodes[n]["sensor"]] for n in sensores}
    nx.draw_networkx_labels(G, pos, labels=rotulos_sensores, font_size=6,
                            font_color="white", ax=ax)

    # Legenda
    legenda = [
        Line2D([], [], marker="o", ls="", color="#444444", ms=12, label="Servidor (posto de enfermagem)"),
        Line2D([], [], marker="o", ls="", color="#1f77b4", ms=12, label="Gateway"),
        Line2D([], [], marker="o", ls="", color="#aaaaaa", mec="black", ms=11, label="Incubadora"),
        Line2D([], [], marker="o", ls="", color="#aaaaaa", mec="black", ms=9, label="Pulseira (neonato)"),
        Line2D([], [], marker="o", ls="", color="#aaaaaa", ms=6,
               label="Sensor  U/T/R = umidade/temp./ruído  T°/O₂/FC = pulseira"),
        Line2D([], [], color=CORES_STATUS["normal"], lw=6, label="Normal"),
        Line2D([], [], color=CORES_STATUS["alerta"], lw=6, label="Alerta"),
        Line2D([], [], color=CORES_STATUS["critico"], lw=6, label="Crítico"),
        Line2D([], [], color="#333333", lw=3, label="Cabo"),
        Line2D([], [], color="#1f77b4", lw=1.8, ls=":", label="Wi-Fi"),
        Line2D([], [], color="#9467bd", lw=1.5, ls="--", label="Bluetooth"),
    ]
    ax.legend(handles=legenda, loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8,
              frameon=False)

    ax.set_title("Grafo de geolocalização - UTI Neonatal (incubadoras, pulseiras e sensores)")
    ax.set_xlim(-0.5, LARGURA_UTI + 0.5)
    ax.set_ylim(-0.5, ALTURA_UTI + 0.5)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)
    fig.tight_layout()
    fig.savefig(ARQUIVO_SAIDA, dpi=150, bbox_inches="tight")
    print(f"Imagem salva em {ARQUIVO_SAIDA}")
    plt.show()


if __name__ == "__main__":
    grafo = montar_grafo()
    imprimir_relatorio(grafo)
    desenhar_grafo(grafo)
