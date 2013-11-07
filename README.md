PR-PR is a new simple way to do biological experiments faster on multiple platforms.

Reuse your scripts for different platforms — Tecan, Microfluidics, even human languages.

Paper: http://pubs.acs.org/doi/abs/10.1021/sb300075t

PR-PR alpha v.032
==================

Simple web mode:
------------------

	python3 setup.py
	python3 ppserver.py

Simple console mode:
------------------

	python3 setup.py
	python3 ppserver.py your_config_file.par

PR-PR google group:
------------------

https://groups.google.com/forum/#!forum/PR-PR



Advanced PR-PR setup and installation
==================

PR-PR has certain customizable parts you can change to your liking to make it work with your Tecan robot.
Currently, there are two customizations supported: plate names and liquid classes (methods).


1. Edit **platesInfo.txt** to reflect plate names and dimensions of your Tecan robot.
2. Edit **methodsInfo.txt** to reflect the liquid classes that are set up with your robot.
3. Follow the simple modes guide.

----
This programming language was previously known as "PaR-PaR", which is not associated with PaR Systems, Inc. which claims ownership of the "PaR" mark.