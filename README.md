PaR-PaR alpha v.03
==================

Simple web mode:
------------------

	python3 setup.py
	python3 ppserver.py

Simple console mode:
------------------

	python3 setup.py
	python3 ppserver.py your_config_file.par

PaR-PaR google group:
------------------

https://groups.google.com/forum/#!forum/par-par



Advanced PaR-PaR setup and installation
==================

PaR-PaR has certain customizable parts you can change to your liking to make it work with your Tecan robot.
Currently, there are two customizations supported: plate names and liquid classes (methods).


1. Edit platesInfo.txt to reflect plate names and dimensions of your Tecan robot.
2. Edit methodsInfo.txt to reflect the liquid classes that are set up with your robot.
3. Follow the simple modes guide.