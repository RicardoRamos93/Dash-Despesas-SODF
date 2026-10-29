# Execução orçamentária: Secretaria de Obras e NOVACAP

Dashboard da execução da despesa das unidades orçamentárias **22101 (Secretaria de Estado de Obras e Infraestrutura do DF)** e **22201 (NOVACAP)**, com dados abertos do SIGGO publicados no Portal de Dados Abertos do GDF.

## Estrutura

```
index.html            o dashboard (HTML + CSS + JavaScript, sem build)
data/*.json           os dados que o dashboard lê
atualizar_dados.py    gera os arquivos de data/ a partir do .zip do portal
```

## Publicar no GitHub Pages (uma vez)

1. Crie uma conta em github.com, se ainda não tiver.
2. Clique em **New repository**, dê um nome (ex.: `dashboard-obras-df`), marque **Public** e clique em **Create repository**.
3. Na página do repositório, clique em **uploading an existing file** e arraste `index.html`, `README.md`, `atualizar_dados.py`, `.gitignore` e a pasta `data` inteira. Clique em **Commit changes**.
4. Vá em **Settings → Pages**. Em **Source**, escolha **Deploy from a branch**; em **Branch**, escolha `main` e a pasta `/ (root)`. Clique em **Save**.
5. Em um ou dois minutos o endereço aparece no topo da mesma tela, no formato `https://SEU-USUARIO.github.io/dashboard-obras-df/`.

## Atualizar os dados

1. Baixe o arquivo novo de despesas em dados.df.gov.br ("[Portal da Transparência] Despesas da Administração Pública do Distrito Federal").
2. Rode, com o pandas instalado (`pip install pandas`):
   ```
   python atualizar_dados.py caminho/para/despesas_2026.csv
   ```
   O arquivo do portal costuma vir com extensão `.csv`, mas é um `.zip`; o script aceita os dois.
3. Envie os arquivos novos da pasta `data/` para o repositório, de um destes jeitos:
   - **Pelo site:** abra a pasta `data` no GitHub, clique em **Add file → Upload files**, arraste os 7 arquivos `.json` e clique em **Commit changes**.
   - **Pelo git:** `git add data && git commit -m "Atualiza dados" && git push`.

O GitHub Pages republica sozinho em cerca de um minuto. A data de extração, o mês parcial e os valores das notas de rodapé se ajustam aos dados novos.

## Ver no próprio computador

Abrir o `index.html` com dois cliques não funciona, porque o navegador bloqueia a leitura dos arquivos de `data/`. Rode um servidor local na pasta do projeto:

```
python -m http.server 8000
```

e abra `http://localhost:8000`.

## Notas sobre os dados

- A tabela principal do SIGGO não traz a unidade orçamentária; o script a atribui pelo programa de trabalho, cruzando com a tabela de empenhos.
- Não há dotação inicial nem autorizada nessa base.
- "Pago" inclui só despesas do próprio exercício (sem restos a pagar).
- A tabela de credores mostra apenas CNPJs; pagamentos a pessoas físicas ficam de fora.
