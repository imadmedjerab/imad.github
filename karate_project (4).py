# karate_project_fixed_v2.py
import PySimpleGUI as sg
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import io
import datetime

# ---------------------------
# Utils: draw matplotlib figure onto a PySimpleGUI Canvas
# ---------------------------
def draw_figure(canvas, figure):
    """Draw a Matplotlib figure onto a PySimpleGUI Canvas element (clears previous)."""
    # Clear previous drawings on that canvas (if any)
    try:
        for child in canvas.TKCanvas.winfo_children():
            child.destroy()
    except Exception:
        pass
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas.TKCanvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

# ---------------------------
# Graph drawing - recomputes layout every draw
# ---------------------------
def draw_graph_figure(G, highlight_nodes=None, figsize=(6,6)):
    """
    Create and return a matplotlib Figure for graph G.
    Recompute spring_layout each time so new nodes get positions.
    """
    pos_local = nx.spring_layout(G, seed=42)
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111)
    ax.set_title("Zachary Karate Club (interactive)")
    # node sizes proportional to degree (plus minimum)
    degs = dict(G.degree())
    node_sizes = [100 + 200 * degs.get(n, 0) for n in G.nodes()]
    node_colors = []
    for n in G.nodes():
        if highlight_nodes and n in highlight_nodes:
            node_colors.append('orange')
        else:
            node_colors.append('lightblue')
    nx.draw_networkx(G, pos=pos_local, ax=ax, with_labels=True,
                     node_size=node_sizes, node_color=node_colors, font_size=8)
    ax.axis('off')
    fig.tight_layout()
    return fig

# ---------------------------
# Adjacency helpers
# ---------------------------
def rebuild_adjacency(G):
    nodes = sorted(G.nodes())
    index_map = {node: i for i, node in enumerate(nodes)}
    n = len(nodes)
    A = np.zeros((n, n), dtype=int)
    for a, b in G.edges():
        i, j = index_map[a], index_map[b]
        A[i, j] = 1
        A[j, i] = 1
    return A, nodes

def adjacency_to_text(A, nodes):
    if len(nodes) == 0:
        return "Graph is empty (no nodes)."
    header = "   " + " ".join(f"{n:>3}" for n in nodes)
    rows = []
    for i, n in enumerate(nodes):
        rows.append(f"{n:>3} " + " ".join(f"{val:>3}" for val in A[i]))
    return header + "\n" + "\n".join(rows)

# ---------------------------
# Parsing helpers
# ---------------------------
def parse_single_int(txt):
    txts = txt.strip()
    if txts == "":
        raise ValueError("empty")
    return int(txts)

def parse_pair(txt):
    parts = [p.strip() for p in txt.split(',')]
    if len(parts) != 2:
        raise ValueError("Expected two comma-separated integers like 'u,v'")
    return int(parts[0]), int(parts[1])

# ---------------------------
# Initial graph
# ---------------------------
G = nx.karate_club_graph()
A, nodes = rebuild_adjacency(G)

# ---------------------------
# GUI layout
# ---------------------------
canvas_col = [[sg.Canvas(key='-CANVAS-', size=(640, 480))]]

controls_col = [
    [sg.Text("Add node (single integer):"), sg.Input(key='-ADDNODE-', size=(10,1)), sg.Button("Add node", key='-ADDNODEBTN-')],
    [sg.Text("Remove node (single integer):"), sg.Input(key='-REMNODE-', size=(10,1)), sg.Button("Remove node", key='-REMNODEBTN-')],
    [sg.HorizontalSeparator()],
    [sg.Text("Add edge (u,v):"), sg.Input(key='-ADDEDGE-', size=(12,1)), sg.Button("Add edge", key='-ADDEDGEBTN-')],
    [sg.Text("Remove edge (u,v):"), sg.Input(key='-REMEDGE-', size=(12,1)), sg.Button("Remove edge", key='-REMEDGEBTN-')],
    [sg.HorizontalSeparator()],
    [sg.Text("Highlight node:"), sg.Input(key='-HIGHLIGHT-', size=(6,1)), sg.Button("Highlight node", key='-HIGHLIGHTBTN-'), sg.Button("Reset highlight", key='-RESET-HL-')],
    [sg.HorizontalSeparator()],
    [sg.Button("Export adjacency (save) ", key='-EXPORT-'), sg.Button("Quit")]
]

log_col = [
    [sg.Multiline(default_text="Log:\n", size=(60, 12), key='-LOG-', autoscroll=True, disabled=False)],
    [sg.Text("Adjacency matrix:")],
    [sg.Multiline(default_text=adjacency_to_text(A, nodes), size=(60, 10), key='-ADJTEXT-', autoscroll=True)]
]

layout = [[sg.Column(canvas_col), sg.Column(controls_col), sg.Column(log_col)]]

window = sg.Window("Interactive Karate Club Graph (v2)", layout, finalize=True, resizable=True)

# ---------------------------
# State
# ---------------------------
fig_agg = None
current_highlight = set()

# ---------------------------
# Central redraw function
# ---------------------------
def redraw():
    global fig_agg
    try:
        fig = draw_graph_figure(G, highlight_nodes=current_highlight)
        fig_agg = draw_figure(window['-CANVAS-'], fig)
        return True, None
    except Exception as e:
        return False, e

def update_adj_display_and_log(msg_prefix=""):
    A_local, nodes_local = rebuild_adjacency(G)
    window['-ADJTEXT-'].update(adjacency_to_text(A_local, nodes_local))
    if msg_prefix:
        window['-LOG-'].print(msg_prefix)

# initial draw
ok, err = redraw()
if not ok:
    window['-LOG-'].print(f"Error drawing initial graph: {err}")
else:
    window['-LOG-'].print("Started. Initial graph drawn.")
update_adj_display_and_log()

# ---------------------------
# Event loop
# ---------------------------
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == "Quit":
        break

    # ---- Add node
    if event == "-ADDNODEBTN-":
        txt = values['-ADDNODE-'] or ""
        try:
            node = parse_single_int(txt)
            if node in G.nodes():
                window['-LOG-'].print(f"Node {node} already exists.")
            else:
                G.add_node(node)
                window['-LOG-'].print(f"Added node {node}.")
        except ValueError as ve:
            window['-LOG-'].print(f"Add node failed: {ve}")
        except Exception as e:
            window['-LOG-'].print(f"Add node invalid input: '{txt}'. Must be integer.")
        update_adj_display_and_log()
        ok, err = redraw()
        if not ok:
            window['-LOG-'].print(f"Error redrawing after add node: {err}")

    # ---- Remove node
    if event == "-REMNODEBTN-":
        txt = values['-REMNODE-'] or ""
        try:
            node = parse_single_int(txt)
            if node not in G.nodes():
                window['-LOG-'].print(f"Node {node} does not exist.")
            else:
                G.remove_node(node)
                window['-LOG-'].print(f"Removed node {node}.")
                # if it was highlighted, remove from highlight set
                if node in current_highlight:
                    current_highlight.discard(node)
        except ValueError as ve:
            window['-LOG-'].print(f"Remove node failed: {ve}")
        except Exception:
            window['-LOG-'].print(f"Invalid remove node input: '{txt}'. Must be integer.")
        update_adj_display_and_log()
        ok, err = redraw()
        if not ok:
            window['-LOG-'].print(f"Error redrawing after remove node: {err}")

    # ---- Add edge
    if event == "-ADDEDGEBTN-":
        txt = values['-ADDEDGE-'] or ""
        try:
            u, v = parse_pair(txt)
            added_nodes = []
            if u not in G.nodes():
                G.add_node(u); added_nodes.append(u)
            if v not in G.nodes():
                G.add_node(v); added_nodes.append(v)
            if G.has_edge(u, v):
                window['-LOG-'].print(f"Edge ({u},{v}) already exists.")
            else:
                G.add_edge(u, v)
                window['-LOG-'].print(f"Added edge ({u},{v}).")
                if added_nodes:
                    window['-LOG-'].print(f"Also added missing nodes {added_nodes}.")
        except ValueError as ve:
            window['-LOG-'].print(f"Add edge failed: {ve}")
        except Exception:
            window['-LOG-'].print(f"Invalid add edge input: '{txt}'. Expected format 'u,v' where u and v are integers.")
        update_adj_display_and_log()
        ok, err = redraw()
        if not ok:
            window['-LOG-'].print(f"Error redrawing after add edge: {err}")

    # ---- Remove edge
    if event == "-REMEDGEBTN-":
        txt = values['-REMEDGE-'] or ""
        try:
            u, v = parse_pair(txt)
            # Check nodes exist
            if u not in G.nodes() or v not in G.nodes():
                window['-LOG-'].print(f"Cannot remove edge ({u},{v}): one or both nodes do not exist.")
            elif not G.has_edge(u, v):
                window['-LOG-'].print(f"Edge ({u},{v}) does not exist.")
            else:
                G.remove_edge(u, v)
                window['-LOG-'].print(f"Removed edge ({u},{v}).")
        except ValueError as ve:
            window['-LOG-'].print(f"Remove edge failed: {ve}")
        except Exception:
            window['-LOG-'].print(f"Invalid remove edge input: '{txt}'. Expected format 'u,v' where u and v are integers.")
        update_adj_display_and_log()
        ok, err = redraw()
        if not ok:
            window['-LOG-'].print(f"Error redrawing after remove edge: {err}")

    # ---- Highlight node
    if event == "-HIGHLIGHTBTN-":
        txt = values['-HIGHLIGHT-'] or ""
        try:
            node = parse_single_int(txt)
            if node not in G.nodes():
                window['-LOG-'].print(f"Cannot highlight {node}: node not in graph.")
            else:
                current_highlight = {node}
                window['-LOG-'].print(f"Highlighted node {node}.")
                ok, err = redraw()
                if not ok:
                    window['-LOG-'].print(f"Error redrawing after highlight: {err}")
        except ValueError as ve:
            window['-LOG-'].print(f"Highlight failed: {ve}")
        except Exception:
            window['-LOG-'].print(f"Invalid highlight input: '{txt}'. Must be integer.")

    # ---- Reset highlight
    if event == "-RESET-HL-":
        current_highlight = set()
        ok, err = redraw()
        if not ok:
            window['-LOG-'].print(f"Error redrawing after reset highlight: {err}")
        else:
            window['-LOG-'].print("Reset highlights.")

    # ---- Export adjacency (save to file)
    if event == "-EXPORT-":
        try:
            A_local, nodes_local = rebuild_adjacency(G)
            txt = adjacency_to_text(A_local, nodes_local)
            # show Save As dialog
            default_fname = f"adjacency_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            save_path = sg.popup_get_file('Save adjacency as', save_as=True, default_extension='.txt',
                                         file_types=(('Text Files', '.txt'),), default_path=default_fname)
            if save_path:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(txt)
                window['-LOG-'].print(f"Adjacency matrix saved to: {save_path}")
            else:
                window['-LOG-'].print("Export cancelled by user.")
            # also echo in log and update adjacency box
            window['-LOG-'].print("Adjacency snapshot:\n" + txt)
            window['-ADJTEXT-'].update(txt)
        except Exception as e:
            window['-LOG-'].print(f"Error exporting adjacency: {e}")

# Cleanup
window.close()
