"""Returns the results for the MDSA algorithm. The results are composed of a
list of nodes that is generated by the Alipour algorithm on the original input
graph, a list of nodes that are selected for the following graphs:
snn_algo_graph adapted_snn_graph rad_snn_algo_graph rad_adapted_snn_graph.

, and a boolean per graph to indicate whether the graphs as computed by Alipour
and the SNN match.

These results are returned in the form of a dict.
"""
import copy
from collections import Counter
from pprint import pprint
from typing import Dict, List, Optional, Tuple, Union

import networkx as nx
from simsnn.core.nodes import LIF
from simsnn.core.simulators import Simulator
from snnbackends.simsnn.run_on_simsnn import (
    get_mdsa_neuron_indices_for_spike_raster,
)
from snncompare.export_plots.create_dash_plot import create_svg_plot
from snncompare.export_results.helper import run_config_to_filename
from snncompare.helper import get_actual_duration
from snncompare.optional_config import Output_config
from snncompare.run_config.Run_config import Run_config
from typeguard import typechecked

from snnalgorithms.sparse.MDSA.get_results import get_results


@typechecked
def set_mdsa_snn_results(
    *,
    m_val: int,
    output_config: Output_config,
    run_config: Run_config,
    stage_2_graphs: Dict,
) -> None:
    """Returns the nodes and counts per node that were computed by the SNN
    algorithm.

    TODO: rewrite to store results in graphs directly.
    """

    # TODO: Verify stage 2 graphs.
    # Get Alipour count.
    # Compute the count for each node according to Alipour et al.'s algorithm.
    alipour_counter_marks = get_results(
        input_graph=stage_2_graphs["input_graph"],
        m_val=m_val,
        rand_props=stage_2_graphs["input_graph"].graph["alg_props"],
        seed=run_config.seed,
        size=run_config.graph_size,
    )

    # Compute SNN results
    for graph_name, snn in stage_2_graphs.items():
        if isinstance(snn, Simulator):
            # graph =
            graph_attributes = snn.network.graph.graph

        else:
            # graph = snn
            graph_attributes = snn.graph
        graph = snn

        # Verify the SNN graphs have completed simulation stage 2.
        if graph_name != "input_graph":
            if 2 not in graph_attributes["completed_stages"]:
                raise ValueError(
                    "Error, the stage 2 simulation is not yet"
                    + f" completed for: {graph_name}"
                )

            if graph_name == "snn_algo_graph":
                graph_attributes["results"] = get_snn_results(
                    alipour_counter_marks=alipour_counter_marks,
                    input_graph=stage_2_graphs["input_graph"],
                    redundant=False,
                    run_config=run_config,
                    snn_graph=graph,
                )
                assert_valid_results(
                    actual_node_names=graph_attributes["results"],
                    expected_node_names=alipour_counter_marks,
                    graphs_dict=stage_2_graphs,
                    output_config=output_config,
                    run_config=run_config,
                    graph_name=graph_name,
                )

            elif graph_name == "adapted_snn_graph":
                graph_attributes["results"] = get_snn_results(
                    alipour_counter_marks=alipour_counter_marks,
                    input_graph=stage_2_graphs["input_graph"],
                    redundant=True,
                    run_config=run_config,
                    snn_graph=graph,
                    red_level=graph_attributes["red_level"],
                )
                assert_valid_results(
                    actual_node_names=graph_attributes["results"],
                    expected_node_names=alipour_counter_marks,
                    graphs_dict=stage_2_graphs,
                    output_config=output_config,
                    run_config=run_config,
                    graph_name=graph_name,
                )

            elif graph_name == "rad_snn_algo_graph":
                graph_attributes["results"] = get_snn_results(
                    alipour_counter_marks=alipour_counter_marks,
                    input_graph=stage_2_graphs["input_graph"],
                    redundant=False,
                    run_config=run_config,
                    snn_graph=graph,
                )
            elif graph_name == "rad_adapted_snn_graph":
                graph_attributes["results"] = get_snn_results(
                    alipour_counter_marks=alipour_counter_marks,
                    input_graph=stage_2_graphs["input_graph"],
                    redundant=True,
                    run_config=run_config,
                    snn_graph=graph,
                    red_level=graph_attributes["red_level"],
                )
            else:
                raise ValueError(f"Invalid graph name:{graph_name}")
            # TODO: verify the results are set correctly.


@typechecked
def assert_valid_results(
    *,
    actual_node_names: Dict,
    expected_node_names: Dict[str, int],
    graph_name: str,
    graphs_dict: Dict,
    output_config: Output_config,
    run_config: Run_config,
    verbose: Optional[bool] = False,
) -> None:
    """Assert results are equal to the Alipour default algorithm."""

    # Remove the passed boolean, and redo results verification.
    copy_actual_node_names = copy.deepcopy(actual_node_names)
    copy_actual_node_names.pop("passed")

    # Verify node names are identical.
    if copy_actual_node_names.keys() != expected_node_names.keys():
        raise KeyError(
            f"Selected SNN node_names for: {graph_name}, are "
            "not equal to the default/Neumann selected nodes:\n"
            f"SNN nodes:    {copy_actual_node_names.keys()}\n"
            "!=\n"
            f"Neumann nodes:{expected_node_names.keys()}\n"
        )

    # Verify the expected nodes are the same as the actual nodes.
    for key in expected_node_names.keys():
        if expected_node_names[key] != copy_actual_node_names[key]:
            # Visualise the snn behaviour
            run_config_filename = run_config_to_filename(
                run_config_dict=run_config.__dict__
            )

            # Override output config from exp_config.
            output_config.extra_storing_config.show_images = True
            output_config.hover_info.neuron_properties = [
                "spikes",
                "a_in",
                "bias",
                "du",
                "u",
                "dv",
                "v",
                "vth",
            ]

            create_svg_plot(
                run_config_filename=run_config_filename,
                graph_names=[graph_name],
                graphs=graphs_dict,
                output_config=output_config,
            )
            raise ValueError(
                f"SNN count per node for: {graph_name}, are not equal to "
                " the default/Neumann node counts:\n"
                f"SNN nodes:    {actual_node_names}\n"
                "!=\n"
                f"Neumann nodes:{expected_node_names}\n"
                f"Node:{key} has different counts."
            )
    if not actual_node_names["passed"]:
        raise ValueError(
            "Error, did not detect a difference between SNN "
            "and Neumann mark count in the nodes. Yet "
            "the results computation says there should be a difference."
        )

    if verbose:
        print("")
        for node_index, expected_count in expected_node_names.items():
            print(
                f"{graph_name}: node_index:{node_index}, ali-mark:"
                + f"{expected_count}, snn:{copy_actual_node_names[node_index]}"
            )


# pylint: disable=R0913
@typechecked
def get_snn_results(
    *,
    alipour_counter_marks: Dict[str, int],
    input_graph: nx.Graph,
    redundant: bool,
    run_config: Run_config,
    snn_graph: Union[nx.DiGraph, Simulator],
    red_level: Optional[int] = None,
) -> Dict:
    """Returns the marks per node that are selected by the snn simulation.

    If the simulation is ran with adaptation in the form of redundancy,
    the code automatically selects the working node, and returns its
    count in the list.
    """
    # Determine why the duration is used here to get a time step.
    sim_duration = get_actual_duration(
        simulator=run_config.simulator, snn_graph=snn_graph
    )
    final_timestep = sim_duration - 1  # Because all indices start at 0.

    snn_counter_marks = {}
    if not redundant:
        snn_counter_marks = get_nx_LIF_count_without_redundancy(
            input_graph=input_graph,
            snn=snn_graph,
            simulator=run_config.simulator,
            t=final_timestep,
        )
    else:
        snn_counter_marks = get_nx_LIF_count_with_redundancy(
            input_graph=input_graph,
            adapted_nx_snn_graph=snn_graph,
            red_level=red_level,
            simulator=run_config.simulator,
            t=final_timestep,
        )

    # Compare the two performances.
    if alipour_counter_marks == snn_counter_marks:
        snn_counter_marks["passed"] = True
    else:
        snn_counter_marks["passed"] = False
    return snn_counter_marks


@typechecked
def get_nx_LIF_count_without_redundancy(
    *,
    input_graph: nx.Graph,
    snn: Union[nx.DiGraph, Simulator],
    simulator: str,
    t: int,
) -> Dict:
    """Creates a dictionary with the node name and the the current as node
    count.

    # TODO: build support for Lava NX neuron.

    :param G: The original graph on which the MDSA algorithm is ran.
    :param snn:
    :param m: The amount of approximation iterations used in the MDSA
    approximation.
    """
    # Initialise the node counts
    node_counts = {}

    # TODO: verify nx simulator is used, throw error otherwise.

    if simulator == "simsnn":
        counter_indices = get_mdsa_neuron_indices_for_spike_raster(
            node_name_identifier="counter",
            snn=snn,
        )
        for counter_index in counter_indices:
            simsnn_node: LIF = snn.network.nodes[counter_index]
            node_counts[simsnn_node.name] = simsnn_node.I
    elif simulator == "nx":
        for node_index in range(0, len(input_graph)):
            node_counts[f"counter_{node_index}"] = int(
                snn.nodes[f"counter_{node_index}"]["nx_lif"][t].u.get()
            )
    return node_counts


@typechecked
def get_nx_LIF_count_with_redundancy(
    *,
    input_graph: nx.Graph,
    adapted_nx_snn_graph: Union[nx.DiGraph, Simulator],
    red_level: int,
    simulator: str,
    t: int,
    majority_vote: Optional[bool] = True,
) -> Dict:
    """Creates a dictionary with the node name and the current as node count.
    This assumes the algorithm was generated with redundancy, and it uses
    majority voting.

    # TODO: build support for Lava NX neuron.

    :param G: The original graph on which the MDSA algorithm is ran.
    :param snn:
    :param m: The amount of approximation iterations used in the MDSA
    approximation.
    """
    # Initialise the node counts.
    node_counts: Dict = {}

    # Verify redundancy level is positive and odd. (E.g. 1,3,5 etc.).
    if red_level < 1 or red_level % 2 == 1:
        raise ValueError(
            "Error, redundancy should be 2 or larger and even, it is:"
            + f"{red_level}."
        )

    # TODO: verify nx simulator is used, throw error otherwise.
    for node_index in range(0, len(input_graph)):
        if not majority_vote:
            get_node_count(
                adapted_nx_snn_graph=adapted_nx_snn_graph,
                node_counts=node_counts,
                node_index=node_index,
                red_level=red_level,
                t=t,
            )
        else:
            node_counts[f"counter_{node_index}"] = get_majority_node_count(
                input_graph=input_graph,
                adapted_snn=adapted_nx_snn_graph,
                node_index=node_index,
                red_level=red_level,
                simulator=simulator,
                t=t,
            )
    return node_counts


@typechecked
def get_node_count(
    *,
    adapted_nx_snn_graph: nx.DiGraph,
    node_counts: Dict,
    node_index: int,
    red_level: int,
    t: int,
) -> None:
    """If a counter neuron fires, which it always does when it gets an input
    signal, if it is working properly.

    If so, it inhibits the redundant counter neurons. So by checking
    whether they have a negative current u, one can see which neuron
    stored the actual count.
    """
    # Check if counterneuron died, if yes, read out redundant neuron.
    if counter_neuron_died(
        snn_graph=adapted_nx_snn_graph,
        counter_neuron_name=f"counter_{node_index}",
    ):
        prefix = f"r_{red_level}_"
    else:
        prefix = ""

    snn_counter_marks: Dict[str, float] = {}
    add_redundant_counter_node_counts(
        adapted_nx_snn_graph=adapted_nx_snn_graph,
        node_index=node_index,
        red_level=red_level,
        snn_counter_marks=snn_counter_marks,
        t=t,
    )

    for node_count in snn_counter_marks.values():
        if node_count >= 0:
            node_counts[f"counter_{node_index}"] = node_count

    node_counts[f"counter_{node_index}"] = adapted_nx_snn_graph.nodes[
        f"{prefix}counter_{node_index}"
    ]["nx_lif"][t].u.get()
    raise SystemError("TODO: verify and document this procedure.")


@typechecked
def add_redundant_counter_node_counts(
    *,
    adapted_nx_snn_graph: nx.DiGraph,
    node_index: int,
    red_level: int,
    snn_counter_marks: Dict[str, float],
    t: int,
) -> Dict[str, float]:
    """Returns the count stored in the redundant counter neurons."""
    for redundancy in list(range(1, red_level + 1)):
        # Get redundant node counts:
        prefix = f"r_{redundancy}_"
        red_node_name = f"{prefix}counter_{node_index}"
        snn_counter_marks[red_node_name] = adapted_nx_snn_graph.nodes[
            red_node_name
        ]["nx_lif"][t].u.get()
    return snn_counter_marks


@typechecked
def get_majority_node_count(
    *,
    input_graph: nx.Graph,
    adapted_snn: Union[nx.DiGraph, Simulator],
    node_index: int,
    red_level: int,
    simulator: str,
    t: int,
    remove_negatives: Optional[bool] = True,
) -> float:
    """Returns the node count according to a majority vote between the original
    and redundant nodes of a count node in the MDSA neuron."""

    snn_counter_marks: Dict[str, int] = get_nx_LIF_count_without_redundancy(
        input_graph=input_graph,
        snn=adapted_snn,
        simulator=simulator,
        t=t,
    )

    # Filter only counter_<node_index> neurons.
    remove_node_names: List[str] = []
    # pylint:disable=C0201
    for node_name in snn_counter_marks.keys():
        if f"counter_{node_index}" not in node_name:
            remove_node_names.append(node_name)
    for node_name in remove_node_names:
        snn_counter_marks.pop(node_name)

    if simulator == "nx":
        add_redundant_counter_node_counts(
            adapted_nx_snn_graph=adapted_snn,
            node_index=node_index,
            red_level=red_level,
            snn_counter_marks=snn_counter_marks,
            t=t,
        )
    pprint(snn_counter_marks)

    if remove_negatives:
        remove_node_names = []
        for node_name, node_count in snn_counter_marks.items():
            if node_count < 0:
                remove_node_names.append(node_name)
        for node_name in remove_node_names:
            snn_counter_marks.pop(node_name)

    # Verify there are at most 2 different values, one for died neurons,
    # and one for functional count neurons.
    if len(set(list(snn_counter_marks.values()))) > 2:
        raise ValueError(
            "Error, the node count contains more than 2 different values."
            "Only a valid, and an invalid value for died neurons may exist."
            f"However, we found:{list(snn_counter_marks.values())}."
        )

    return find_majority(votes=list(snn_counter_marks.values()), position=1)[
        0
    ]  # Return value that occurred most.


@typechecked
def find_majority(*, votes: List[float], position: int) -> Tuple[float, int]:
    """Returns the value, and number of votes in the list of numbers. First
    place is position=1 (not 0).

    Negatives may be removed because they are from inhibited counter neurons.

    Return index 0 is the value. Return index 1 is how often that value
    is in the list.
    """
    vote_count = Counter(votes)
    return vote_count.most_common(position)[0]  # Unpack list into Tuple.


@typechecked
def counter_neuron_died(
    *, snn_graph: nx.DiGraph, counter_neuron_name: str
) -> bool:
    """Returns True if the counter neuron died, and False otherwise. This
    method assumes the chip is able to probe a particular neuron to determine
    if it is affected by radiation or not, after the algorithm is completed.

    Alternatively, a majority voting amongst 3 or more redundant neurons
    may be used to read out the algorithm results.
    """

    # Determine whether the graph has rad_death property:
    if graph_has_dead_neurons(snn_graph=snn_graph):
        return snn_graph.nodes[counter_neuron_name]["rad_death"]
    return False


@typechecked
def graph_has_dead_neurons(*, snn_graph: nx.DiGraph) -> bool:
    """Checks whether the "rad_death" key is in any of the nodes of the graph,
    and if it is, verifies it is in all of the nodes."""
    rad_death_found = False
    for node_name in snn_graph.nodes:
        if "rad_death" in snn_graph.nodes[node_name].keys():
            rad_death_found = True

    if rad_death_found:
        for node_name in snn_graph.nodes:
            if "rad_death" not in snn_graph.nodes[node_name].keys():
                raise KeyError(
                    "Error, rad_death key not set in all nodes of"
                    + "graph, yet it was set for at least one node in graph:"
                    + f"{snn_graph}"
                )

        return True
    return False
