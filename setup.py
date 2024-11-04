

from setuptools import setup
from setuptools import find_packages

tests_require = ["pytest"]

long_description = """"""


setup(name="ffpie",
      description="a FFmpeg emulator built on pyav",
      long_description=long_description,
      license="BSD",
      version="1.0.0",
      author="Allen Ling",
      author_email="allenling3@gmail.com",
      maintainer="Allen Ling",
      maintainer_email="allenling3@gmail.com",
      url="https://github.com/allenling/ffpie",
      packages=find_packages(include=["ffpie", "ffpie.*"]),
      tests_require=tests_require,
      extras_require={"test": tests_require},
      install_requires=["av>=13.0.0", "redis"],
      python_requires=">= 3.9",
      classifiers=[
          "Programming Language :: Python :: 3",
          "Framework :: Pytest",
      ])




def main():
    return


if __name__ == "__main__":
    main()
