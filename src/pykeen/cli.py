"""A command line interface for PyKEEN.

Why does this file exist, and why not put this in ``__main__``? You might be tempted to import things from ``__main__``
later, but that will cause problems - the code will get executed twice:

- When you run ``python -m pykeen`` python will execute``__main__.py`` as a script. That means there won't be any
  ``pykeen.__main__`` in ``sys.modules``.
- When you import __main__ it will get executed again (as a module) because there's no ``pykeen.__main__`` in
  ``sys.modules``.

.. seealso::

    http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

import importlib
import inspect
import os
import sys
from collections.abc import Iterable, Mapping
from operator import itemgetter
from pathlib import Path
from typing import Any, TypeVar

import click
from class_resolver import ClassResolver
from class_resolver.contrib.optuna import sampler_resolver
from click_default_group import DefaultGroup
from docdata import get_docdata
from tabulate import tabulate

from .datasets import dataset_resolver
from .datasets.inductive import inductive_dataset_resolver
from .evaluation import (
    ClassificationMetricResults,
    MetricResults,
    RankBasedMetricResults,
    evaluator_resolver,
    metric_resolver,
)
from .experiments.cli import experiments
from .hpo.cli import optimize
from .losses import loss_resolver
from .lr_schedulers import lr_scheduler_resolver
from .metrics.utils import Metric
from .models import model_resolver
from .models.cli import build_cli_from_cls
from .nn import representation_resolver
from .nn.modules import interaction_resolver
from .nn.node_piece.cli import tokenize
from .nn.pyg import MessagePassingRepresentation
from .optimizers import optimizer_resolver
from .regularizers import regularizer_resolver
from .sampling import negative_sampler_resolver
from .stoppers import stopper_resolver
from .trackers import tracker_resolver
from .training import training_loop_resolver
from .triples.utils import EXTENSION_IMPORTER_RESOLVER, PREFIX_IMPORTER_RESOLVER
from .utils import get_until_first_blank, getattr_or_docdata
from .version import env_table

HERE = Path(__file__).resolve().parent
X = TypeVar("X")


@click.group()
def main() -> None:
    """PyKEEN."""


@main.command()
@click.option("-f", "--tablefmt", default="github", show_default=True)
def version(tablefmt: str) -> None:
    """Print version information for debugging."""
    click.echo(env_table(tablefmt))


tablefmt_option = click.option("-f", "--tablefmt", default="plain", show_default=True)


@main.group(cls=DefaultGroup, default="github-readme", default_if_no_args=True)
def ls() -> None:
    """List implementation details."""


@ls.command()
@tablefmt_option  # type:ignore
def models(tablefmt: str) -> None:
    """List models."""
    click.echo(_help_models(tablefmt=tablefmt)[0])


def format_class(cls: type, module: str | None = None) -> str:
    """Generate the fully-qualified class name.

    :param cls: the class
    :param module: the module name to use instead of `cls.__module__`

    :returns: the fully qualified class name
    """
    if module is None:
        module = cls.__module__
    return f"{module}.{cls.__qualname__}"


def _citation(dd):
    citation = (dd or {}).get("citation")
    if citation is None:
        return None
    return f"[{citation['author']} *et al.*, {citation['year']}]({citation['link']})"


def _format_reference(reference: str | None, link_fmt: str | None, alt_reference: str | None = None) -> str:
    """Format a reference.

    :param reference: the reference
    :param link_fmt: the link format
    :param alt_reference: the link target. Defaults to the reference.

    :returns: a Markdown reference
    """
    if reference is None:
        return ""
    if link_fmt is None:
        return f"`{reference}`"
    return f"[`{reference}`]({link_fmt.format(alt_reference or reference)})"


def _get_resolver_lines2(
    resolver: ClassResolver[X],
    link_fmt: str | None = None,
    skip: set[type[X]] | None = None,
    top_k: int = 2,
) -> Iterable[tuple[str, str, str | None]]:
    for _, clsx in sorted(resolver.lookup_dict.items()):
        if skip and clsx in skip:
            continue
        # determine fully qualified name
        module, name = clsx.__module__, clsx.__qualname__
        if "pykeen.nn.meta" in module:
            continue
        full = f"{module}.{name}"
        # shorten to main module
        if top_k:
            module = ".".join(module.split(".", maxsplit=top_k)[:-1])
        short = f"{module}.{name}"
        # verify that short name can be imported from the abbreviated reference
        if name not in dir(importlib.import_module(module)):
            click.secho(message=f"{name} not visible in {module}", err=True)
        # get docdata and extract name & citation
        docdata = resolver.docdata(clsx) or {}
        assert isinstance(docdata, dict)
        # fallback for name: capitalized class name without base suffix
        name = docdata.get("name", clsx.__name__.replace(resolver.base.__name__, ""))
        assert isinstance(name, str)
        # extract citation information and warn about lack thereof
        citation = _citation(docdata)
        if not citation:
            click.secho(message=f"Missing citation for {short}", err=True)
        # compose reference
        reference = _format_reference(reference=short, link_fmt=link_fmt, alt_reference=full)
        yield name, reference, citation


def _help_models(tablefmt: str = "github", *, link_fmt: str | None = None) -> tuple[str, int]:
    lines = sorted(_get_resolver_lines2(resolver=model_resolver, link_fmt=link_fmt))
    headers = ["Name", "Model", "Citation"]
    return (
        tabulate(
            lines,
            headers=headers,
            tablefmt=tablefmt,
        ),
        len(lines),
    )


def _help_interactions(tablefmt: str = "github", *, link_fmt: str | None = None) -> tuple[str, int]:
    lines = list(
        _get_resolver_lines2(
            resolver=interaction_resolver,
            link_fmt=link_fmt,
        )
    )
    headers = ["Name", "Reference", "Citation"]
    return (
        tabulate(
            lines,
            headers=headers,
            tablefmt=tablefmt,
        ),
        len(lines),
    )


def _help_representations(tablefmt: str = "github", *, link_fmt: str | None = None) -> tuple[str, int]:
    lines = list(
        line[:2]
        for line in _get_resolver_lines2(
            resolver=representation_resolver,
            link_fmt=link_fmt,
            # cf. https://github.com/python/mypy/issues/5374
            skip={MessagePassingRepresentation},  # type: ignore
        )
    )
    headers = ["Name", "Reference"]
    return (
        tabulate(
            lines,
            headers=headers,
            tablefmt=tablefmt,
        ),
        len(lines),
    )


@ls.command()
def importers() -> None:
    """List triple importers."""
    for prefix, f in sorted(PREFIX_IMPORTER_RESOLVER.lookup_dict.items()):
        click.secho(f"prefix: {prefix} from {_get_module_name(f)}")
    for suffix, f in sorted(EXTENSION_IMPORTER_RESOLVER.lookup_dict.items()):
        click.secho(f"suffix: {suffix} from {_get_module_name(f)}")


def _get_module_name(f: Any) -> str:
    m = inspect.getmodule(f)
    if m:
        return m.__name__
    return "<module not found>"


@ls.command()
@tablefmt_option  # type:ignore
@click.option("--sort-size", is_flag=True)
def datasets(tablefmt: str, sort_size: bool) -> None:
    """List datasets."""
    click.echo(_help_datasets(tablefmt, sort_size=sort_size))


def _help_datasets(tablefmt: str, link_fmt: str | None = None, sort_size: bool = False):
    lines = _get_dataset_lines(tablefmt=tablefmt, link_fmt=link_fmt)
    if sort_size:
        lines = sorted(lines, key=lambda line: line[5], reverse=True)
    return tabulate(
        lines,
        headers=["Name", "Documentation", "Citation", "Entities", "Relations", "Triples"],
        tablefmt=tablefmt,
    )


def _help_inductive_datasets(tablefmt: str, link_fmt: str | None = None):
    lines = _get_inductive_dataset_lines(tablefmt=tablefmt, link_fmt=link_fmt)
    return tabulate(
        lines,
        headers=["Name", "Documentation", "Citation"],
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def training_loops(tablefmt: str) -> None:
    """List training approaches."""
    click.echo(_help_training(tablefmt))


def _help_training(tablefmt: str, link_fmt: str | None = None):
    lines = _get_resolver_lines(training_loop_resolver.lookup_dict, tablefmt, "training", link_fmt=link_fmt)
    return tabulate(
        lines,
        headers=["Name", "Description"] if tablefmt == "plain" else ["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def negative_samplers(tablefmt: str) -> None:
    """List negative samplers."""
    click.echo(_help_negative_samplers(tablefmt))


def _help_negative_samplers(tablefmt: str, link_fmt: str | None = None):
    lines = _get_resolver_lines(negative_sampler_resolver.lookup_dict, tablefmt, "sampling", link_fmt=link_fmt)
    return tabulate(
        lines,
        headers=["Name", "Description"] if tablefmt == "plain" else ["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def stoppers(tablefmt: str) -> None:
    """List stoppers."""
    click.echo(_help_stoppers(tablefmt))


def _help_stoppers(tablefmt: str, link_fmt: str | None = None):
    lines = _get_resolver_lines(stopper_resolver.lookup_dict, tablefmt, "stoppers", link_fmt=link_fmt)
    return tabulate(
        lines,
        headers=["Name", "Description"] if tablefmt == "plain" else ["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def evaluators(tablefmt: str) -> None:
    """List evaluators."""
    click.echo(_help_evaluators(tablefmt))


def _help_evaluators(tablefmt, link_fmt: str | None = None):
    lines = sorted(_get_resolver_lines(evaluator_resolver.lookup_dict, tablefmt, "evaluation", link_fmt=link_fmt))
    return tabulate(
        lines,
        headers=["Name", "Description"] if tablefmt == "plain" else ["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def losses(tablefmt: str) -> None:
    """List losses."""
    click.echo(_help_losses(tablefmt))


def _help_losses(tablefmt: str, link_fmt: str | None = None):
    lines = _get_lines_alternative(tablefmt, loss_resolver.lookup_dict, "torch.nn", "pykeen.losses", link_fmt)
    return tabulate(
        lines,
        headers=["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def optimizers(tablefmt: str) -> None:
    """List optimizers."""
    click.echo(_help_optimizers(tablefmt))


def _help_optimizers(tablefmt: str, link_fmt: str | None = None):
    lines = _get_lines_alternative(
        tablefmt,
        optimizer_resolver.lookup_dict,
        "torch.optim",
        "pykeen.optimizers",
        link_fmt=link_fmt,
    )
    return tabulate(
        lines,
        headers=["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def lr_schedulers(tablefmt: str) -> None:
    """List optimizers."""
    click.echo(_help_lr_schedulers(tablefmt))


def _help_lr_schedulers(tablefmt: str, link_fmt: str | None = None):
    lines = _get_lines_alternative(
        tablefmt,
        lr_scheduler_resolver.lookup_dict,
        "torch.optim.lr_scheduler",
        "pykeen.lr_schedulers",
        link_fmt=link_fmt,
    )
    return tabulate(
        lines,
        headers=["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def regularizers(tablefmt: str) -> None:
    """List regularizers."""
    click.echo(_help_regularizers(tablefmt))


def _help_regularizers(tablefmt, link_fmt: str | None = None) -> str:
    lines = _get_resolver_lines(regularizer_resolver.lookup_dict, tablefmt, "regularizers", link_fmt=link_fmt)
    return tabulate(
        lines,
        headers=["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


def _get_lines_alternative(tablefmt, d, torch_prefix, pykeen_prefix, link_fmt: str | None = None):
    for name, cls in sorted(d.items()):
        if any(cls.__module__.startswith(_prefix) for _prefix in ("torch", "optuna")):
            path = f"{torch_prefix}.{cls.__qualname__}"
        else:  # from pykeen
            path = f"{pykeen_prefix}.{cls.__qualname__}"

        docdata = get_docdata(cls)
        if docdata is not None:
            name = docdata.get("name", name)

        if tablefmt == "rst":
            yield name, f":class:`{path}`"
        elif tablefmt == "github":
            doc = cls.__doc__
            if link_fmt:
                reference = f"[`{path}`]({link_fmt.format(path)})"
            else:
                reference = f"`{path}`"

            yield name, reference, get_until_first_blank(doc)
        else:
            doc = cls.__doc__
            yield name, path, get_until_first_blank(doc)


@ls.command()
@tablefmt_option  # type:ignore
def metrics(tablefmt: str) -> None:
    """List metrics."""
    click.echo(_help_metrics(tablefmt))


def _help_metrics(tablefmt: str) -> str:
    headers = [
        "Name",
        "Interval",
        "Direction",
        "Description",
        "Type",
        # "Closed-Form Expectation",
        # "Closed-Form Variance",
    ]
    if tablefmt != "github":
        headers.append("Reference")
        headers[0] = "Metric"
    return tabulate(
        sorted(_get_metrics_lines(tablefmt), key=itemgetter(4, 0)),  # type:ignore
        headers=headers,
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def trackers(tablefmt: str) -> None:
    """List trackers."""
    click.echo(_help_trackers(tablefmt))


def _help_trackers(tablefmt: str, link_fmt: str | None = None) -> str:
    lines = _get_resolver_lines(tracker_resolver.lookup_dict, tablefmt, "trackers", link_fmt=link_fmt)
    return tabulate(
        lines,
        headers=["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


@ls.command()
@tablefmt_option  # type:ignore
def hpo_samplers(tablefmt: str) -> None:
    """List HPO samplers."""
    click.echo(_help_hpo_samplers(tablefmt))


def _help_hpo_samplers(tablefmt: str, link_fmt: str | None = None) -> str:
    lines = _get_lines_alternative(
        tablefmt,
        sampler_resolver.lookup_dict,
        "optuna.samplers",
        "pykeen.hpo.samplers",
        link_fmt=link_fmt,
    )
    return tabulate(
        lines,
        headers=["Name", "Reference", "Description"],
        tablefmt=tablefmt,
    )


METRIC_NAMES: Mapping[type[MetricResults], str] = {
    ClassificationMetricResults: "Classification",
    RankBasedMetricResults: "Ranking",
}

METRICS_SKIP: set[str] = {"standard_deviation", "variance", "median_absolute_deviation", "count"}


def _get_metrics_lines(tablefmt: str) -> Iterable[tuple[str, ...]]:
    for key, metric, metric_results_cls in get_metric_list():
        if key in METRICS_SKIP:
            continue
        label = getattr_or_docdata(metric, "name")
        link = getattr_or_docdata(metric, "link")
        yv = [
            f"[{label}]({link})",
            "$" + metric.get_range() + "$",
            "📈" if metric.increasing else "📉",
            getattr_or_docdata(metric, "description"),
            METRIC_NAMES[metric_results_cls],
            # "✓" if metric.closed_expectation else "",
            # "✓" if metric.closed_variance else "",
        ]
        if tablefmt != "github":
            yv.append(f"pykeen.evaluation.{metric_results_cls.__name__}")
        yield tuple(yv)


def _get_resolver_lines(
    d: Mapping[str, type[X]], tablefmt: str, submodule: str, link_fmt: str | None = None
) -> Iterable[tuple[str, str]] | Iterable[tuple[str, str, str | None]]:
    for name, value in sorted(d.items()):
        if tablefmt == "rst":
            if isinstance(value, type):
                reference = f":class:`pykeen.{submodule}.{value.__name__}`"
            else:
                reference = f":class:`pykeen.{submodule}.{name}`"

            yield name, reference
        elif tablefmt == "github":
            try:
                ref = value.__name__
                doc = value.__doc__.splitlines()[0]  # type: ignore
            except AttributeError:
                ref = name
                doc = value.__class__.__doc__

            reference = f"pykeen.{submodule}.{ref}"
            if link_fmt:
                reference = f"[`{reference}`]({link_fmt.format(reference)})"
            else:
                reference = f"`{reference}`"

            yield name, reference, doc
        else:
            assert isinstance(value.__doc__, str)
            yield name, value.__doc__.splitlines()[0]


def _get_dataset_lines(tablefmt, link_fmt: str | None = None) -> Iterable[tuple[str, ...]]:
    for name, value in sorted(dataset_resolver.lookup_dict.items()):
        reference = f"pykeen.datasets.{value.__name__}"
        if tablefmt == "rst":
            reference = f":class:`{reference}`"
        elif link_fmt is not None:
            reference = f"[`{reference}`]({link_fmt.format(reference)})"
        else:
            reference = f"`{reference}`"

        docdata = get_docdata(value)
        if docdata is None:
            yield name, reference, "", "", "", ""
            continue

        name = docdata["name"]
        statistics = docdata["statistics"]
        entities = statistics["entities"]
        relations = statistics["relations"]
        triples = statistics["triples"]

        citation_str = ""
        citation = docdata.get("citation")
        if citation is not None:
            author = citation and citation.get("author")
            year = citation and citation.get("year")
            link = citation and citation.get("link")
            github = citation and citation.get("github")
            if author and year and link:
                _citation_txt = f"{author.capitalize()} *et al*., {year}"
                citation_str = _link(_citation_txt, link, tablefmt)
            elif github:
                link = f"https://github.com/{github}"
                citation_str = _link(github if tablefmt == "rst" else f"`{github}`", link, tablefmt)
        yield name, reference, citation_str, entities, relations, triples


def _get_inductive_dataset_lines(tablefmt, link_fmt: str | None = None) -> Iterable[tuple[str, ...]]:
    for name, value in sorted(inductive_dataset_resolver.lookup_dict.items()):
        reference = f"pykeen.datasets.{value.__name__}"
        if tablefmt == "rst":
            reference = f":class:`{reference}`"
        elif link_fmt is not None:
            reference = f"[`{reference}`]({link_fmt.format(reference)})"
        else:
            reference = f"`{reference}`"

        docdata = get_docdata(value)
        if docdata is None:
            yield name, reference, "", "", "", ""
            continue

        name = docdata["name"]

        citation_str = ""
        citation = docdata.get("citation")
        if citation is not None:
            author = citation and citation.get("author")
            year = citation and citation.get("year")
            link = citation and citation.get("link")
            github = citation and citation.get("github")
            if author and year and link:
                _citation_txt = f"{author.capitalize()} *et al*., {year}"
                citation_str = _link(_citation_txt, link, tablefmt)
            elif github:
                link = f"https://github.com/{github}"
                citation_str = _link(github if tablefmt == "rst" else f"`{github}`", link, tablefmt)
        yield name, reference, citation_str


def _link(text: str, link: str, fmt: str) -> str:
    if fmt == "rst":
        return f"`{text} <{link}>`_"
    else:
        return f"[{text}]({link})"


def get_metric_list() -> list[tuple[str, type[Metric], type[MetricResults]]]:
    """Get info about all metrics across all evaluators."""
    return [
        (metric_key, metric_cls, resolver_cls)
        for resolver_cls in metric_resolver
        for metric_key, metric_cls in resolver_cls.metrics.items()
    ]


@main.command()
@click.option("--check", is_flag=True)
def readme(check: bool) -> None:
    """Generate the GitHub readme's ## Implementation section."""
    readme_path = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, "README.md"))
    new_readme = get_readme()

    if check:
        with open(readme_path, encoding="utf8") as file:
            old_readme = file.read()
        if new_readme.strip() != old_readme.strip():
            click.secho(
                "Readme has not been updated properly! Make sure all changes are made in the template first,"
                " and see the following diff:",
                fg="red",
            )
            import difflib

            for x in difflib.context_diff(new_readme.splitlines(), old_readme.splitlines()):
                click.echo(x)

            sys.exit(-1)

    with open(readme_path, "w", encoding="utf8") as file:
        print(new_readme, file=file)  # noqa:T201


def get_readme() -> str:
    """Get the readme."""
    from jinja2 import Environment, FileSystemLoader

    loader = FileSystemLoader(HERE.joinpath("templates"))
    environment = Environment(
        autoescape=True,
        loader=loader,
        trim_blocks=False,
    )
    readme_template = environment.get_template("README.md")
    tablefmt = "github"
    api_link_fmt = "https://pykeen.readthedocs.io/en/latest/api/{}.html"
    models, n_models = _help_models(tablefmt, link_fmt=api_link_fmt)
    interactions, n_interactions = _help_interactions(tablefmt, link_fmt=api_link_fmt)
    representations, n_representations = _help_representations(tablefmt, link_fmt=api_link_fmt)
    return readme_template.render(
        interactions=interactions,
        n_interactions=n_interactions,
        representations=representations,
        n_representations=n_representations,
        models=models,
        n_models=n_models,
        regularizers=_help_regularizers(tablefmt, link_fmt=api_link_fmt),
        n_regularizers=len(regularizer_resolver.lookup_dict),
        losses=_help_losses(tablefmt, link_fmt=api_link_fmt),
        n_losses=len(loss_resolver.lookup_dict),
        datasets=_help_datasets(tablefmt, link_fmt=api_link_fmt),
        n_datasets=len(dataset_resolver.lookup_dict),
        inductive_datasets=_help_inductive_datasets(tablefmt, link_fmt=api_link_fmt),
        n_inductive_datasets=len(inductive_dataset_resolver.lookup_dict),
        training_loops=_help_training(
            tablefmt,
            link_fmt="https://pykeen.readthedocs.io/en/latest/reference/training.html#{}",
        ),
        n_training_loops=len(training_loop_resolver.lookup_dict),
        negative_samplers=_help_negative_samplers(
            tablefmt,
            link_fmt=api_link_fmt,
        ),
        n_negative_samplers=len(negative_sampler_resolver.lookup_dict),
        stoppers=_help_stoppers(
            tablefmt,
            link_fmt="https://pykeen.readthedocs.io/en/latest/reference/stoppers.html#{}",
        ),
        n_stoppers=len(stopper_resolver.lookup_dict),
        evaluators=_help_evaluators(tablefmt, link_fmt=api_link_fmt),
        n_evaluators=len(evaluator_resolver.lookup_dict),
        metrics=_help_metrics(tablefmt),
        n_metrics=len(get_metric_list()),
        trackers=_help_trackers(tablefmt, link_fmt=api_link_fmt),
        n_trackers=len(tracker_resolver.lookup_dict),
    )


@main.group()  # type:ignore
@click.pass_context  # type:ignore
def train(ctx: click.Context) -> None:
    """Train a KGE model."""


for cls in model_resolver.lookup_dict.values():
    train.add_command(build_cli_from_cls(cls))

# Add HPO command
main.add_command(optimize)
main.add_command(experiments)

# Add NodePiece tokenization command
main.add_command(tokenize)

if __name__ == "__main__":
    main()
