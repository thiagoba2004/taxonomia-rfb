import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Configuração da página
st.set_page_config(
    page_title="Taxonomia da RFB", page_icon="🌳", layout="wide"
)

# Estilização mínima da página host (o visual da árvore em si vive dentro do
# componente HTML/JS embutido logo abaixo, isolado em seu próprio iframe)
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {
        background-color: #f3f6fa !important;
    }

    .main-title {
        font-size: 2.6rem !important;
        font-weight: 800 !important;
        color: #111827 !important;
        margin-bottom: 0px !important;
    }
    .sub-title {
        color: #4b5563 !important;
        font-size: 1.15rem !important;
        margin-bottom: 1.2rem !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="main-title">Taxonomia de Assuntos da RFB</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-title">Navegação hierárquica interativa em cartões'
    " (renderizada em HTML/JS para fluidez total, sem recarregar a"
    " página a cada clique)</p>",
    unsafe_allow_html=True,
)


@st.cache_data
def carregar_dados():
  df = pd.read_csv("taxonomia_rfb.csv", sep=";", encoding="utf-8")
  df["ID"] = df["ID"].astype(str)
  df["Pai"] = (
      df["Pai"]
      .fillna("")
      .astype(str)
      .apply(lambda x: x.split(".")[0] if x != "" else "")
  )
  df["Nome"] = df["Nome"].fillna("").astype(str)
  df["Tipo"] = df["Tipo"].fillna("").astype(str)
  if "Caminho Completo" not in df.columns:
    df["Caminho Completo"] = df["Nome"]
  df["Caminho Completo"] = df["Caminho Completo"].fillna(df["Nome"]).astype(str)
  return df


# Modelo HTML/CSS/JS autocontido da árvore de cartões.
# "__DADOS_JSON__" é substituído pelos dados reais antes de renderizar.
# Usamos .replace() (em vez de f-string) para não ter que escapar todas as
# chaves { } do CSS/JS.
COMPONENTE_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<style>
  html, body {
    margin: 0;
    padding: 0;
    background: #f3f6fa;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    color: #1f2937;
  }

  #buscaInput {
    width: 100%;
    box-sizing: border-box;
    padding: 10px 14px;
    font-size: 1rem;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    margin-bottom: 14px;
    outline: none;
    transition: border-color .15s ease, box-shadow .15s ease;
  }
  #buscaInput:focus {
    border-color: #93bab5;
    box-shadow: 0 0 0 3px rgba(147,186,181,0.25);
  }
  #infoBusca {
    color: #4b5563;
    font-size: 0.9rem;
    margin-bottom: 10px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 14px;
    align-items: stretch;
    margin-bottom: 6px;
  }

  @keyframes surgirCartao {
    from { opacity: 0; transform: translateY(8px) scale(0.98); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }

  .card-topico {
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    transition: transform .18s ease, box-shadow .18s ease;
    animation: surgirCartao .28s ease;
    cursor: default;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: center;
    height: 100%;
  }
  .card-topico:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.14);
  }
  .card-icone { font-size: 1.5em; margin-bottom: 4px; }
  .card-titulo {
    font-weight: 700;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    word-break: break-word;
  }
  .card-id { font-size: 0.72em; opacity: 0.7; margin-top: 4px; color: #4b5563; }

  .btn-toggle {
    display: block;
    width: 100%;
    margin: 8px 0 16px 0;
    padding: 6px 10px;
    font-size: 0.82rem;
    border-radius: 8px;
    border: 1px solid #d1d5db;
    background: #ffffff;
    cursor: pointer;
    transition: background-color .15s ease, border-color .15s ease;
  }
  .btn-toggle:hover { background: #eef2f7; border-color: #9ca3af; }

  /* Painel de filhos: animação de altura via CSS Grid (0fr -> 1fr), suave e sem JS de medição */
  .children-wrapper {
    display: grid;
    grid-template-rows: 0fr;
    transition: grid-template-rows .32s ease;
    margin-bottom: 4px;
  }
  .children-wrapper.aberto { grid-template-rows: 1fr; }
  .children-inner {
    overflow: hidden;
    min-height: 0;
    border-left: 3px solid #d1d5db;
    padding-left: 14px;
    margin-left: 2px;
  }
</style>
</head>
<body>

  <input type="text" id="buscaInput" placeholder="🔍 Busca rápida (digite para filtrar direto)"
         oninput="realizarBusca(this.value)">
  <div id="infoBusca"></div>

  <div id="arvore"></div>
  <div id="resultados" style="display:none;"></div>

<script>
  const DADOS = __DADOS_JSON__;

  // Cor de fundo por categoria — tons dessaturados, matizes bem separados
  const CORES = {
    raiz: "#a9c1d1",
    dominio: "#d1ab8a",
    area: "#a7c3a0",
    subarea: "#d3bd85",
    divisao: "#b3a3c4",
    especialidade: "#cf9fac",
    tema: "#93bab5",
    subtema: "#b6907a",
    outro: "#c3c7cc",
  };

  // Tamanho de fonte (rem) por categoria — ordem fixa e decrescente
  const FONTES = {
    raiz: 1.9,
    dominio: 1.55,
    area: 1.35,
    subarea: 1.2,
    divisao: 1.1,
    especialidade: 1.02,
    tema: 0.95,
    subtema: 0.88,
  };
  const FONTE_PADRAO_OUTRO = 0.82;
  const FONTE_MINIMA = 0.75;

  function tamanhoFonte(categoria, depth) {
    if (categoria in FONTES) return FONTES[categoria];
    const extra = Math.max(0, depth - Object.keys(FONTES).length);
    return Math.max(FONTE_MINIMA, FONTE_PADRAO_OUTRO - 0.03 * extra);
  }

  function classificar(tipoOriginal) {
    const tipo = (tipoOriginal || "").toLowerCase();
    if (tipo.includes("domínio") || tipo.includes("dominio"))
      return { cat: "dominio", icone: "📚", prefixo: "GRANDE DOMÍNIO" };
    if (tipo.includes("subárea") || tipo.includes("subarea"))
      return { cat: "subarea", icone: "📑", prefixo: "Subárea" };
    if (tipo.includes("área") || tipo.includes("area"))
      return { cat: "area", icone: "📖", prefixo: "Área" };
    if (tipo.includes("divisão") || tipo.includes("divisao"))
      return { cat: "divisao", icone: "🔹", prefixo: "Divisão" };
    if (tipo.includes("especialidade"))
      return { cat: "especialidade", icone: "🔸", prefixo: "Especialidade" };
    if (tipo.includes("subtema"))
      return { cat: "subtema", icone: "📎", prefixo: "Subtema" };
    if (tipo.includes("tema"))
      return { cat: "tema", icone: "📌", prefixo: "Tema" };
    return { cat: "outro", icone: "🔹", prefixo: "Item" };
  }

  function escapeHtml(texto) {
    return String(texto ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Indexa filhos por ID do pai
  const childrenMap = {};
  DADOS.forEach((r) => {
    const pai = r.Pai || "";
    if (!childrenMap[pai]) childrenMap[pai] = [];
    childrenMap[pai].push(r);
  });

  // Raízes: mesma lógica de fallback usada na versão Python original
  let raizes = DADOS.filter((r) => r.Pai === "" || r.Pai === "nan");
  if (raizes.length === 0) {
    raizes = DADOS.filter((r) => r.ID === "0");
  }
  childrenMap[""] = raizes;

  function buildNode(record, depth) {
    const id = record.ID;
    const { cat, icone, prefixo } = classificar(record.Tipo);
    const fonte = tamanhoFonte(cat, depth);
    const cor = CORES[cat] || CORES.outro;
    const filhos = childrenMap[id] || [];
    const temFilhos = filhos.length > 0;

    const container = document.createElement("div");

    const card = document.createElement("div");
    card.className = "card-topico";
    card.style.background = cor;
    card.innerHTML =
      '<div class="card-icone">' + icone + "</div>" +
      '<div class="card-titulo" style="font-size:' + fonte + 'rem;">' +
        escapeHtml(prefixo) + ": " + escapeHtml(record.Nome) +
      "</div>" +
      '<div class="card-id">ID: ' + escapeHtml(id) + "</div>";
    container.appendChild(card);

    if (temFilhos) {
      const btn = document.createElement("button");
      btn.className = "btn-toggle";
      btn.id = "arrow-" + id;
      btn.textContent = "▼ Expandir";
      btn.onclick = () => toggleNode(id, depth + 1);
      container.appendChild(btn);

      const wrap = document.createElement("div");
      wrap.className = "children-wrapper";
      wrap.id = "wrap-" + id;
      const inner = document.createElement("div");
      inner.className = "children-inner";
      wrap.appendChild(inner);
      container.appendChild(wrap);
    }

    return container;
  }

  function buildGrid(parentId, depth) {
    const filhos = childrenMap[parentId] || [];
    const grid = document.createElement("div");
    grid.className = "grid";
    filhos.forEach((rec) => grid.appendChild(buildNode(rec, depth)));
    return grid;
  }

  function toggleNode(id, childDepth) {
    const wrapper = document.getElementById("wrap-" + id);
    const arrow = document.getElementById("arrow-" + id);
    const abrir = !wrapper.classList.contains("aberto");

    if (abrir) {
      if (wrapper.dataset.built !== "1") {
        const inner = wrapper.querySelector(".children-inner");
        inner.appendChild(buildGrid(id, childDepth));
        wrapper.dataset.built = "1";
      }
      wrapper.classList.add("aberto");
      arrow.textContent = "▲ Recolher";
    } else {
      wrapper.classList.remove("aberto");
      arrow.textContent = "▼ Expandir";
    }
    setTimeout(ajustarAltura, 360);
  }

  function realizarBusca(termoOriginal) {
    const termo = termoOriginal.trim().toLowerCase();
    const arvoreEl = document.getElementById("arvore");
    const resultadosEl = document.getElementById("resultados");
    const infoEl = document.getElementById("infoBusca");

    if (!termo) {
      arvoreEl.style.display = "";
      resultadosEl.style.display = "none";
      resultadosEl.innerHTML = "";
      infoEl.textContent = "";
      ajustarAltura();
      return;
    }

    const achados = DADOS.filter((r) =>
      (r.CaminhoCompleto || r.Nome || "").toLowerCase().includes(termo)
    );

    arvoreEl.style.display = "none";
    resultadosEl.style.display = "";
    infoEl.textContent =
      "Mostrando " + achados.length + ' resultado(s) para "' + termoOriginal + '"';

    const grid = document.createElement("div");
    grid.className = "grid";
    achados.forEach((r) => {
      const { cat, icone } = classificar(r.Tipo);
      const cor = CORES[cat] || CORES.outro;
      const card = document.createElement("div");
      card.className = "card-topico";
      card.style.background = cor;
      card.innerHTML =
        '<div class="card-icone">' + icone + "</div>" +
        '<div class="card-titulo" style="font-size:1.05rem;">' + escapeHtml(r.Nome) + "</div>" +
        '<div class="card-id">' + escapeHtml(r.Tipo) + "</div>" +
        '<div class="card-id">' + escapeHtml(r.CaminhoCompleto || "") + "</div>";
      grid.appendChild(card);
    });

    resultadosEl.innerHTML = "";
    resultadosEl.appendChild(grid);
    ajustarAltura();
  }

  function ajustarAltura() {
    try {
      const altura = document.body.scrollHeight;
      if (window.frameElement) {
        window.frameElement.style.height = (altura + 24) + "px";
      }
    } catch (e) {
      /* ambiente sem acesso ao frame pai — ignora silenciosamente */
    }
  }

  // Render inicial (nível raiz)
  document.getElementById("arvore").appendChild(buildGrid("", 0));

  window.addEventListener("load", ajustarAltura);
  window.addEventListener("resize", ajustarAltura);
  ajustarAltura();
</script>
</body>
</html>
"""


try:
  df = carregar_dados()

  registros = (
      df[["ID", "Pai", "Nome", "Tipo", "Caminho Completo"]]
      .rename(columns={"Caminho Completo": "CaminhoCompleto"})
      .to_dict(orient="records")
  )
  dados_json = json.dumps(registros, ensure_ascii=False)

  html_final = COMPONENTE_HTML.replace("__DADOS_JSON__", dados_json)

  # A altura é reajustada automaticamente pelo próprio JS (função ajustarAltura),
  # este valor inicial é só o ponto de partida antes do primeiro ajuste.
  components.html(html_final, height=900, scrolling=True)

except FileNotFoundError:
  st.error(
      "O arquivo 'taxonomia_rfb.csv' não foi encontrado na pasta do projeto."
  )