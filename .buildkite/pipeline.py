import yaml

DOCKER_PLUGIN = "docker#v3.1.0"


# This should be an enum once we make our own buildkite AMI with py3
class SupportedPython:
    V3_7 = "3.7"
    V3_6 = "3.6"
    V3_5 = "3.5"
    V2_7 = "2.7"


SupportedPythons = [
    SupportedPython.V3_7,
    SupportedPython.V3_6,
    SupportedPython.V3_5,
    SupportedPython.V2_7,
]

IMAGE_MAP = {
    SupportedPython.V3_7: "python:3.7",
    SupportedPython.V3_6: "python:3.6",
    SupportedPython.V3_5: "python:3.5",
    SupportedPython.V2_7: "python:2.7",
}

TOX_MAP = {
    SupportedPython.V3_7: "py37",
    SupportedPython.V3_6: "py36",
    SupportedPython.V3_5: "py35",
    SupportedPython.V2_7: "py27",
}


class StepBuilder:
    def __init__(self, label):
        self._step = {"label": label}

    def run(self, *argc):
        self._step["command"] = "\n".join(argc)
        return self

    def onImage(self, img):
        if img in IMAGE_MAP:
            img = IMAGE_MAP[img]
        self._step["plugins"] = [{DOCKER_PLUGIN: {"image": img}}]
        return self

    def withEnvironVar(self, var):
        self._step["env"] = {var: "${{{}?}}".format(var)}
        return self

    def build(self):
        return self._step


def wait_step():
    return "wait"


def python_modules_tox_tests(directory, prereqs=None):
    label = directory.replace("/", "-")
    tests = []
    for version in SupportedPythons:
        coverage = ".coverage.{}.{}.$BUILDKITE_BUILD_ID".format(label, version)
        tox_command = []
        if prereqs:
            tox_command += prereqs
        tox_command += [
            "pip install tox;",
            "cd python_modules/{}".format(directory),
            "tox -e {}".format(TOX_MAP[version]),
            "mv .coverage {}".format(coverage),
            "buildkite-agent artifact upload {}".format(coverage),
        ]
        tests.append(
            StepBuilder("{} tests ({})".format(directory, TOX_MAP[version]))
            .run(*tox_command)
            .onImage(version)
            .build()
        )

    return tests


if __name__ == "__main__":
    steps = [
        StepBuilder("pylint")
        .run("make dev_install", "make pylint")
        .onImage(SupportedPython.V3_7)
        .build(),
        StepBuilder("black")
        .run("pip install black==18.9b0", "make check_black")
        .onImage(SupportedPython.V3_7)
        .build(),
        StepBuilder("docs snapshot test")
        .run(
            "pip install -r python_modules/dagster/dev-requirements.txt -qqq",
            "pip install -e python_modules/dagster -qqq",
            "pytest -vv python_modules/dagster/docs",
        )
        .onImage(SupportedPython.V3_7)
        .build(),
        StepBuilder("dagit webapp tests")
        .run(
            "pip install -r python_modules/dagster/dev-requirements.txt -qqq",
            "pip install -e python_modules/dagster -qqq",
            "pip install -e python_modules/dagster-graphql -qqq",
            "pip install -e python_modules/dagit -qqq",
            "pip install -r python_modules/dagit/dev-requirements.txt -qqq",
            "cd js_modules/dagit",
            "yarn install --offline",
            "yarn run ts",
            "yarn run jest",
            "yarn run check-prettier",
            "yarn generate-types",
            "git diff --exit-code",
        )
        .onImage("nikolaik/python-nodejs:python3.7-nodejs11")
        .build(),
    ]
    steps += python_modules_tox_tests("dagster")
    steps += python_modules_tox_tests("dagit", ["apt-get update", "apt-get install -y xdg-utils"])
    steps += python_modules_tox_tests("dagster-graphql")
    steps += python_modules_tox_tests("dagstermill")
    steps += python_modules_tox_tests("libraries/dagster-pandas")
    steps += python_modules_tox_tests("libraries/dagster-ge")
    steps += python_modules_tox_tests("libraries/dagster-aws")
    steps += python_modules_tox_tests("libraries/dagster-snowflake")
    steps += python_modules_tox_tests("libraries/dagster-spark")

    steps += [
        wait_step(),  # wait for all previous steps to finish
        StepBuilder("coverage")
        .run(
            "pip install coverage coveralls",
            "mkdir -p tmp",
            'buildkite-agent artifact download ".coverage*" tmp/',
            "cd tmp",
            "coverage combine",
            "coveralls",
        )
        .withEnvironVar('COVERALLS_REPO_TOKEN')
        .onImage(SupportedPython.V3_7)
        .build(),
    ]

    print(yaml.dump({"steps": steps}, default_flow_style=False, default_style="|"))
