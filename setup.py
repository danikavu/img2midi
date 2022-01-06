from setuptools import setup

setup(
	name='img2midi',
	version='1.0.0',
	author='Daniel Kavoulakos',
	author_email='dan_kavoulakos@hotmail.com',
	description='Convert images to midi',
	license='MIT',
	packages=['.img2midi'],
    package_data={'.img2midi': ['scales/*']},
	install_requires=['numpy',
					  'pandas',
                      'Pillow',
                      'scipy',
                      'note-seq',
					  ],
	python_requires='>=3.7',
)
					  