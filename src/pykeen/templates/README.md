<p align="center">
  <img src="docs/source/logo.png" height="150">
</p>

<h1 align="center">
  PyKEEN
</h1>

<p align="center">
  <a href="https://travis-ci.com/pykeen/pykeen">
    <img src="https://travis-ci.com/pykeen/pykeen.svg?token=2tyMYiCcZbjqYscNWXwZ&branch=master"
         alt="Travis CI">
  </a>

  <a href='https://opensource.org/licenses/MIT'>
    <img src='https://img.shields.io/badge/License-MIT-blue.svg' alt='License'/>
  </a>

  <a href="https://zenodo.org/badge/latestdoi/242672435">
    <img src="https://zenodo.org/badge/242672435.svg" alt="DOI">
  </a>

  <a href="https://badge.fury.io/py/pykeen">
    <img src="https://badge.fury.io/py/pykeen.svg" alt="PyPI version" height="18">
  </a>
</p>

<p align="center">
    <b>PyKEEN</b> (<b>P</b>ython <b>K</b>nowl<b>E</b>dge <b>E</b>mbeddi<b>N</b>gs) is a Python package designed to
    train and evaluate knowledge graph embedding models (incorporating multi-modal information). It is part of the
    <a href="https://github.com/pykeen">KEEN Universe</a>.
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quickstart">Quickstart</a> •
  <a href="#datasets-{{ n_datasets }}">Datasets</a> •
  <a href="#models-{{ n_models }}">Models</a> •
  <a href="#supporters">Support</a>
</p>

## Installation

The development version of PyKEEN can be downloaded and installed from
[PyPI](https://pypi.org/project/pykeen/) on Python 3.7+ with:

```bash
$ pip install pykeen
```

The development version of PyKEEN can be downloaded and installed from
[GitHub](https://github.com/pykeen/pykeen) on Python 3.7+ with:

```bash
$ git clone https://github.com/pykeen/pykeeen.git pykeen
$ cd pykeen
$ pip install -e .
$ # Install pre-commit
$ pip install pre-commit
$ pre-commit install
```

## Contributing

Contributions, whether filing an issue, making a pull request, or forking, are appreciated. 
See [CONTRIBUTING.md](/CONTRIBUTING.md) for more information on getting involved.

## Quickstart [![Documentation Status](https://readthedocs.org/projects/pykeen/badge/?version=latest)](https://pykeen.readthedocs.io/en/latest/?badge=latest)

This example shows how to train a model on a data set and test on another data set.

The fastest way to get up and running is to use the pipeline function. It
provides a high-level entry into the extensible functionality of this package.
The following example shows how to train and evaluate the TransE model on the
Nations dataset. By default, the training loop uses the stochastic local closed world assumption (sLCWA) training
approach and evaluates with rank-based evaluation.

```python
from pykeen.pipeline import pipeline
result = pipeline(
    model='TransE',
    dataset='nations',
)
```

The results are returned in a dataclass that has attributes for the trained
model, the training loop, and the evaluation.

PyKEEN is extensible such that:

- Each model has the same API, so anything from ``pykeen.models`` can be dropped in
- Each training loop has the same API, so ``pykeen.training.LCWATrainingLoop`` can be dropped in
- Triples factories can be generated by the user with ``from pykeen.triples.TriplesFactory``

## Implementation

Below are the models, data sets, training modes, evaluators, and metrics implemented
in ``pykeen``.

### Datasets ({{ n_datasets }})

{{ datasets }}

### Models ({{ n_models }})

{{ models }}

### Losses ({{ n_losses }})

{{ losses }}

### Regularizers ({{ n_regularizers }})

{{ regularizers }}

### Optimizers ({{ n_optimizers }})

{{ optimizers }}

### Training Loops ({{ n_training_loops }})

{{ training_loops }}

### Negative Samplers ({{ n_negative_samplers }})

{{ negative_samplers }}

### Stoppers ({{ n_stoppers }})

{{ stoppers }}

### Evaluators ({{ n_evaluators }})

{{ evaluators }}

### Metrics ({{ n_metrics }})

{{ metrics }}

## Hyper-parameter Optimization

### Samplers ({{ n_hpo_samplers }})

{{ hpo_samplers }}

## Experimentation

### Reproduction

PyKEEN includes a set of curated experimental settings for reproducing past landmark
experiments. They can be accessed and run like:

```bash
pykeen experiments reproduce tucker balazevic2019 fb15k
```

Where the three arguments are the model name, the reference, and the data set.
The output directory can be optionally set with `-d`.

### Ablation

PyKEEN includes the ability to specify ablation studies using the
hyper-parameter optimization module. They can be run like:

```bash
pykeen experiments ablation ~/path/to/config.json
```

## Acknowledgements

### Supporters

This project has been supported by several organizations (in alphabetical order):

- [Bayer](https://www.bayer.com/)
- [Enveda Therapeutics](https://envedatherapeutics.com/)
- [Fraunhofer Institute for Algorithms and Scientific Computing](https://www.scai.fraunhofer.de)
- [Fraunhofer Institute for Intelligent Analysis and Information Systems](https://www.iais.fraunhofer.de)
- [Fraunhofer Center for Machine Learning](https://www.cit.fraunhofer.de/de/zentren/maschinelles-lernen.html)
- [Ludwig-Maximilians-Universität München](https://www.en.uni-muenchen.de/index.html)
- [Munich Center for Machine Learning (MCML)](https://mcml.ai/)
- [Smart Data Analytics Research Group (University of Bonn & Fraunhofer IAIS)](https://sda.tech)
- [Technical University of Denmark - DTU Compute - Section for Cognitive Systems](https://www.compute.dtu.dk/english/research/research-sections/cogsys)
- [Technical University of Denmark - DTU Compute - Section for Statistics and Data Analysis](https://www.compute.dtu.dk/english/research/research-sections/stat)
- [University of Bonn](https://www.uni-bonn.de/)

### Logo

The PyKEEN logo was designed by Carina Steinborn.