import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import altair as alt
    import dlt

    return alt, dlt, mo


@app.cell
def _(mo):
    mo.md("""
    # Claude Code Usage Dashboard
    """)
    return


@app.cell
def _(dlt):
    pipeline = dlt.attach("claude_logs_pipeline")
    dataset = pipeline.dataset()
    return (dataset,)


@app.cell
def _(mo):
    mo.md("""
    ## Activity Over Time
    """)
    return


@app.cell
def _(dataset):
    df_chart1 = dataset("""
        SELECT
            DATE_TRUNC('hour', timestamp) AS hour,
            COUNT(*) AS events
        FROM sessions
        GROUP BY 1
        ORDER BY 1
    """).df()
    return (df_chart1,)


@app.cell
def _(alt, df_chart1):
    _chart = alt.Chart(df_chart1).mark_line(point=True).encode(
        x=alt.X("hour:T", title="Hour"),
        y=alt.Y("events:Q", title="Log entries"),
        tooltip=["hour:T", "events:Q"]
    ).properties(title="Activity Over Time")
    _chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## Message Types Breakdown
    """)
    return


@app.cell
def _(dataset):
    df_chart2 = dataset("""
        SELECT
            type,
            COUNT(*) AS records
        FROM sessions
        GROUP BY 1
        ORDER BY records DESC
    """).df()
    return (df_chart2,)


@app.cell
def _(alt, df_chart2):
    _chart = alt.Chart(df_chart2).mark_bar().encode(
        x=alt.X("records:Q", title="Log entries"),
        y=alt.Y("type:N", sort="-x", title="Type"),
        tooltip=["type:N", "records:Q"]
    ).properties(title="Message Types Breakdown")
    _chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## Token Usage by Model
    """)
    return


@app.cell
def _(dataset):
    df_chart3 = dataset("""
        SELECT message__model AS model, 'input' AS token_type, SUM(message__usage__input_tokens) AS tokens
        FROM sessions
        WHERE message__model IS NOT NULL
        GROUP BY 1, 2
        UNION ALL
        SELECT message__model AS model, 'output' AS token_type, SUM(message__usage__output_tokens) AS tokens
        FROM sessions
        WHERE message__model IS NOT NULL
        GROUP BY 1, 2
    """).df()
    return (df_chart3,)


@app.cell
def _(alt, df_chart3):
    _chart = alt.Chart(df_chart3).mark_bar().encode(
        x=alt.X("model:N", title="Model"),
        y=alt.Y("tokens:Q", title="Tokens", stack="zero"),
        color=alt.Color("token_type:N", title="Token type"),
        tooltip=["model:N", "token_type:N", "tokens:Q"]
    ).properties(title="Token Usage by Model")
    _chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## Top Projects by Activity
    """)
    return


@app.cell
def _(dataset):
    df_chart4 = dataset("""
        SELECT
            cwd,
            COUNT(*) AS records
        FROM sessions
        WHERE cwd IS NOT NULL
        GROUP BY 1
        ORDER BY records DESC
    """).df()
    return (df_chart4,)


@app.cell
def _(alt, df_chart4):
    _chart = alt.Chart(df_chart4).mark_bar().encode(
        x=alt.X("records:Q", title="Log entries"),
        y=alt.Y("cwd:N", sort="-x", title="Project (cwd)"),
        tooltip=["cwd:N", "records:Q"]
    ).properties(title="Top Projects by Activity")
    _chart
    return


if __name__ == "__main__":
    app.run()
