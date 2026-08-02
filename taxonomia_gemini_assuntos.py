import pandas as pd

# Lê o arquivo CSV utilizando o separador ponto e vírgula
df = pd.read_csv('taxonomia_rfb.csv', sep=';', encoding='utf-8')

# Mostra as primeiras linhas para confirmar a importação
print(df.head())

# Exemplo de consulta: Buscar tudo de Direito Tributário (ID pai/raiz 1030303)
df_tributario = df[df['Caminho Completo'].str.contains('Direito Tributário')]
print(df_tributario)