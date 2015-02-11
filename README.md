wquantiles
==========

[![Build Status](https://travis-ci.org/nudomarinero/wquantiles.svg?branch=master)](https://travis-ci.org/nudomarinero/wquantiles)
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.14952.svg)](http://dx.doi.org/10.5281/zenodo.14952)
[![Pypi](https://pypip.in/v/wquantiles/badge.png)](https://pypi.python.org/pypi/wquantiles)

Weighted quantiles with Python, including weighted median. 
This library is based on numpy, which is the only dependence.

The main methods are **quantile** and **median**. The input of 
quantile is a numpy array (_data_), a numpy array of weights of one 
dimension and the value of the quantile (between 0 and 1) to 
compute. The weighting is applied along the last axis. The method 
**median** is an alias to _quantile(data, weights, 0.5)_. 


