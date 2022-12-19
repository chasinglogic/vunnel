import json
import os
import shutil

import pytest

from vunnel.providers.wolfi import Config, Provider, parser
from vunnel.providers.wolfi.parser import Parser


class TestParser:
    @pytest.fixture
    def mock_raw_data(self, helpers):
        """
        Returns stringified version of the following json

        ---
        """
        data = {
            "apkurl": "{{urlprefix}}/{{reponame}}/{{arch}}/{{pkg.name}}-{{pkg.ver}}.apk",
            "archs": ["x86_64"],
            "reponame": "os",
            "urlprefix": "https://packages.wolfi.dev",
            "packages": [
                {
                    "pkg": {
                        "name": "binutils",
                        "secfixes": {
                            "2.39-r1": ["CVE-2022-38126"],
                            "2.39-r2": ["CVE-2022-38533"],
                            "2.39-r3": ["CVE-2022-38128"],
                        },
                    }
                },
                {
                    "pkg": {
                        "name": "brotli",
                        "secfixes": {"1.0.9-r0": ["CVE-2020-8927"]},
                    }
                },
                {
                    "pkg": {
                        "name": "busybox",
                        "secfixes": {"1.35.0-r3": ["CVE-2022-28391", "CVE-2022-30065"]},
                    }
                },
                {"pkg": {"name": "coreutils", "secfixes": {"0": ["CVE-2016-2781"]}}},
                {"pkg": {"name": "cups", "secfixes": {"2.4.2-r0": ["CVE-2022-26691"]}}},
                {
                    "pkg": {
                        "name": "dbus",
                        "secfixes": {
                            "1.14.4-r0": [
                                "CVE-2022-42010",
                                "CVE-2022-42011",
                                "CVE-2022-42012",
                            ]
                        },
                    }
                },
            ],
        }

        return json.dumps(data)

    @pytest.fixture
    def mock_parsed_data(self):
        """
        Returns the parsed output generated by AlpineDataProvider._load() for the mock_raw_data

        :return:
        """
        release = "rolling"
        dbtype_data_dict = {
            "os": {
                "apkurl": "{{urlprefix}}/{{reponame}}/{{arch}}/{{pkg.name}}-{{pkg.ver}}.apk",
                "archs": ["x86_64"],
                "reponame": "os",
                "urlprefix": "https://packages.wolfi.dev",
                "packages": [
                    {
                        "pkg": {
                            "name": "binutils",
                            "secfixes": {
                                "2.39-r1": ["CVE-2022-38126"],
                                "2.39-r2": ["CVE-2022-38533"],
                                "2.39-r3": ["CVE-2022-38128"],
                            },
                        }
                    },
                    {
                        "pkg": {
                            "name": "brotli",
                            "secfixes": {"1.0.9-r0": ["CVE-2020-8927"]},
                        }
                    },
                    {
                        "pkg": {
                            "name": "busybox",
                            "secfixes": {"1.35.0-r3": ["CVE-2022-28391", "CVE-2022-30065"]},
                        }
                    },
                    {
                        "pkg": {
                            "name": "coreutils",
                            "secfixes": {"0": ["CVE-2016-2781"]},
                        }
                    },
                    {
                        "pkg": {
                            "name": "cups",
                            "secfixes": {"2.4.2-r0": ["CVE-2022-26691"]},
                        }
                    },
                    {
                        "pkg": {
                            "name": "dbus",
                            "secfixes": {
                                "1.14.4-r0": [
                                    "CVE-2022-42010",
                                    "CVE-2022-42011",
                                    "CVE-2022-42012",
                                ]
                            },
                        }
                    },
                ],
            }
        }
        return release, dbtype_data_dict

    def test_load(self, mock_raw_data, tmpdir):
        provider = Parser(workspace=tmpdir)

        a = os.path.join(provider.secdb_dir_path, "rolling/os")
        os.makedirs(a, exist_ok=True)
        b = os.path.join(a, "security.json")
        with open(b, "w") as fp:
            fp.write(mock_raw_data)

        counter = 0
        for release, dbtype_data_dict in provider._load():
            counter += 1
            # print(
            #     "got secdb data for release {}, db types: {}".format(
            #         release, list(dbtype_data_dict.keys())
            #     )
            # )
            assert release == "rolling"
            assert isinstance(dbtype_data_dict, dict)
            assert list(dbtype_data_dict.keys()) == ["os"]
            assert all("packages" in x for x in dbtype_data_dict.values())

        assert counter == 1

    def test_normalize(self, mock_parsed_data, tmpdir):
        provider = Parser(workspace=tmpdir)
        release = mock_parsed_data[0]
        dbtype_data_dict = mock_parsed_data[1]

        vuln_records = provider._normalize(release, dbtype_data_dict)
        assert len(vuln_records) > 0
        assert all(map(lambda x: "Vulnerability" in x, vuln_records.values()))
        assert sorted(list(vuln_records.keys())) == sorted(
            [
                "CVE-2016-2781",
                "CVE-2020-8927",
                "CVE-2022-26691",
                "CVE-2022-28391",
                "CVE-2022-30065",
                "CVE-2022-38126",
                "CVE-2022-38128",
                "CVE-2022-38533",
                "CVE-2022-42010",
                "CVE-2022-42011",
                "CVE-2022-42012",
            ]
        )


@pytest.fixture
def disable_get_requests(monkeypatch):
    def disabled(*args, **kwargs):
        raise RuntimeError("requests disabled but HTTP GET attempted")

    monkeypatch.setattr(parser.requests, "get", disabled)


def test_provider_schema(helpers, disable_get_requests):
    workspace = helpers.provider_workspace(name=Provider.name())

    provider = Provider(root=workspace.root, config=Config())

    mock_data_path = helpers.local_dir("test-fixtures/input")
    shutil.copytree(mock_data_path, workspace.input_dir, dirs_exist_ok=True)

    provider.update()

    assert 50 == workspace.num_result_entries()
    assert workspace.result_schemas_valid(require_entries=True)
