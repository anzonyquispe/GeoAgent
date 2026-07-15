# geo-agent 🔥🌲

Agente de Análisis Geoespacial para analizar y visualizar datos de incendios forestales en Perú (NASA VIIRS-SNPP / FIRMS).

El repo está organizado como una serie de clases progresivas, cada una agregando una capa nueva:

| Carpeta | Contenido |
|---|---|
| [deepagents/clase1](deepagents/clase1) | Notebooks introductorios: agente simple y agente con tools básicas |
| [deepagents/clase2](deepagents/clase2) | Agente con `SKILL.md` (tools de descarga/limpieza de datos de incendios) |
| [deepagents/clase3](deepagents/clase3) | App de chat en Streamlit con extracción estructurada (Pydantic) y mapas interactivos (Folium) |
| [deepagents/clase4](deepagents/clase4) | Servidor MCP (`server.py`) para exponer las mismas tools a Claude Desktop |

Todas las clases usan las mismas tools de fondo: descargar datos de incendios de NASA FIRMS, cruzarlos con los límites administrativos de Perú (GADM) y generar mapas coropléticos.

## Requisitos previos

- **Python 3.12** (ver [.python-version](.python-version))
- **[uv](https://docs.astral.sh/uv/)** para manejar el entorno y las dependencias
- **[LM Studio](https://lmstudio.ai/)** corriendo localmente con un modelo cargado (usado por clase 2 y 3 como LLM local vía API compatible con OpenAI en `http://127.0.0.1:1234/v1`)
- Conexión a internet (las tools descargan datos en vivo de NASA FIRMS y GADM)

## Instalación

### macOS

```bash
# 1. Instalar uv (si no lo tienes)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clonar el repo
git clone <URL-del-repo>
cd geo-agent

# 3. Instalar dependencias (crea el entorno virtual automáticamente)
uv sync
```

### Windows

```powershell
# 1. Instalar uv (si no lo tienes) - PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Clonar el repo
git clone <URL-del-repo>
cd geo-agent

# 3. Instalar dependencias (crea el entorno virtual automáticamente)
uv sync
```

> `uv sync` lee [pyproject.toml](pyproject.toml) y [uv.lock](uv.lock) y crea el entorno virtual en `.venv/` con las versiones exactas ya resueltas.

## Servidor MCP para Claude Desktop (clase4)

El servidor expone las mismas tools por MCP para que Claude Desktop pueda usarlas directamente.

1. Abre la configuración de Claude Desktop (`claude_desktop_config.json`):
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Agrega el servidor apuntando a la ruta local de `uv` y del repo, por ejemplo:

   ```json
   {
     "mcpServers": {
       "peru-wildfire-analysis": {
         "command": "uv",
         "args": [
           "run",
           "--directory",
           "/ruta/absoluta/a/geo-agent",
           "python",
           "deepagents/clase4/server.py"
         ]
       }
     }
   }
   ```

   En Windows, usa la ruta absoluta con el formato de Windows, por ejemplo `C:\\Users\\tu-usuario\\geo-agent`.

3. Reinicia Claude Desktop. Las tools (`download_viirs_snpp_peru`, `fires_clean`, `download_ctry_shp`, `intersect_and_collapse_fires_peru`, `plot_fires_choropleth_peru`, `analyze_peru_fires`) quedarán disponibles en el chat.

## Licencia

[MIT](LICENSE)
