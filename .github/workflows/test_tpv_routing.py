"""Routing regressions using real TPV matching and lightweight Galaxy objects.

Run against the rendered job configuration (as in TPV CI):
python .github/workflows/test_tpv_routing.py /path/to/rendered/job_conf.yml
"""

import logging
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from jinja2 import Environment, meta

# The adjacent CI helper tpv.py must not shadow the installed TPV package.
sys.path.remove(str(Path(__file__).resolve().parent))
from tpv.core.loader import TPVConfigLoader
from tpv.core.mapper import EntityToDestinationMapper

logging.getLogger("tpv").setLevel(logging.WARNING)

JOB_CONF = Path(sys.argv.pop(1))


def load_config():
    loader = None
    if JOB_CONF.is_dir():
        root = JOB_CONF
        sources = [
            "tool_defaults.yml",
            "https://raw.githubusercontent.com/galaxyproject/tpv-shared-database/main/tools.yml",
            "destinations.yml",
            "tools.yml",
            "interactive_tools.yml",
            "conda_in_container.yml",
            "users.yml",
            "roles.yml",
        ]
    else:
        job_conf = yaml.safe_load(JOB_CONF.read_text())
        sources = job_conf["execution"]["environments"]["tpv_dispatcher"][
            "tpv_config_files"
        ]

    for source in sources:
        if source.startswith("https://"):
            loader = TPVConfigLoader.from_url_or_path(source, parent=loader)
            continue
        path = root / source if JOB_CONF.is_dir() else Path(source)
        if not path.exists():
            path = path.with_suffix(".yml.j2")
            template = path.read_text()
            environment = Environment(trim_blocks=True, lstrip_blocks=True)
            variables = {
                key: "fixture"
                for key in meta.find_undeclared_variables(
                    environment.parse(template)
                )
            }
            volume = {"name": "db", "path": "/fixture", "docker_perm": "ro"}
            variables.update(
                dnb={"db": volume, 5: volume},
                cache={"cache08": volume},
                tools={"tools": volume},
                cvmfs={"data": volume, "singularity": volume},
                job_working_directory_pool=[
                    {"value": "/fixture", "weight": 1}
                ],
            )
            content = environment.from_string(template).render(variables)
            loader = TPVConfigLoader(yaml.safe_load(content), parent=loader)
            continue
        loader = TPVConfigLoader.from_url_or_path(str(path), parent=loader)
    return EntityToDestinationMapper(loader)


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapper = load_config()
        cls.remote = {
            destination.id
            for destination in cls.mapper.destinations.values()
            if not destination.abstract
            and "pulsar" in destination.tpv_dest_tags.accept
            and "cz-pulsar" not in destination.tpv_dest_tags.require
        }

    def candidates(
        self,
        tool_id="ordinary_cpu",
        *,
        site=None,
        tool_type="default",
        params=None,
        requires_galaxy=False,
        resubmitted=False,
        roles=(),
        final=False,
        rank_override=False,
        fallback=False,
    ):
        tool = SimpleNamespace(
            id=tool_id,
            tool_type=tool_type,
            version=tool_id.rsplit("/", 1)[-1] if "/" in tool_id else "1.0",
            requires_galaxy_python_environment=requires_galaxy,
            dynamic_tool=None,
            resource_requirements=[],
        )
        user = (
            None
            if site is None
            else SimpleNamespace(
                id=1,
                email="routing@example.org",
                all_roles=lambda: [
                    SimpleNamespace(name=name, deleted=False) for name in roles
                ],
                extra_preferences={
                    "distributed_compute|remote_resources": site
                },
            )
        )
        job = SimpleNamespace(
            id=42,
            state="resubmitted" if resubmitted else "new",
            destination_params=(
                {"OOM_MEM_SCALE": 128, "pulsar_local_fallback": fallback}
                if resubmitted
                else {}
            ),
            input_datasets=[],
            get_param_values=lambda app: params or {},
        )
        context = dict(
            self.mapper.global_context,
            tool=tool,
            user=user,
            job=job,
            job_wrapper=object(),
            app=None,
            mapper=self.mapper,
        )
        # TIaaS queries are unrelated to routing and require a live database.
        with patch("psycopg2.connect") as connect:
            connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchall.return_value = (
                []
            )
            entity = self.mapper.match_combine_evaluate_entities(
                context, tool, user
            )
        if rank_override:
            entity.rank = "candidate_destinations"
        # Inspect all candidates deterministically; separately check the actual
        # weight values passed to the sampling helper.
        with patch(
            "tpv.core.helpers.weighted_random_sampling",
            side_effect=lambda values: values,
        ):
            candidates = self.mapper.match_and_rank_destinations(
                entity, self.mapper.destinations, context
            )
        if final:
            destination = candidates[0].combine(entity).evaluate(context)
            return self.mapper.to_galaxy_destination(destination)
        return candidates

    def test_cpu_pool_and_weights(self):
        candidates = self.candidates()
        names = {d.id for d in candidates}
        self.assertEqual(len(self.remote), 15)
        self.assertEqual(names, self.remote | {"condor_container"})
        self.assertEqual(
            next(d for d in candidates if d.id == "condor_container").params[
                "weight"
            ],
            90,
        )
        self.assertTrue(
            all(
                (d.params or {}).get("weight", 1) == 1
                for d in candidates
                if d.id in self.remote
            )
        )

    def test_each_explicit_remote_site(self):
        for name in self.remote:
            destination = self.mapper.destinations[name]
            site = next(
                tag
                for tag in destination.tpv_dest_tags.accept
                if tag.endswith("-pulsar")
            )
            with self.subTest(site=site):
                self.assertEqual(
                    [d.id for d in self.candidates(site=site)], [name]
                )

    def test_local_only_tools_ignore_remote_preference(self):
        cases = (
            (
                "interactive_tool_jupyter_notebook",
                {"tool_type": "interactive"},
            ),
            ("user_defined-example", {}),
            ("last_example", {}),
            ("CONVERTER_gff_to_bed_0", {}),
            ("galaxy_internal", {"requires_galaxy": True}),
            ("data_source", {"tool_type": "data_source"}),
            ("barchart_gnuplot", {}),
        )
        for tool_id, options in cases:
            for site in ("None", "it03-pulsar"):
                with self.subTest(tool=tool_id, site=site):
                    candidates = self.candidates(tool_id, site=site, **options)
                    self.assertTrue(candidates)
                    self.assertFalse({d.id for d in candidates} & self.remote)

    def test_dynamic_gpu_request(self):
        tool_id = "toolshed.g2.bx.psu.edu/repos/bgruening/tabpfn/tabpfn/1.0"
        for gpu in (False, True):
            with self.subTest(gpu=gpu):
                candidates = self.candidates(
                    tool_id,
                    site="it03-pulsar",
                    params={
                        "__job_resource": {
                            "__job_resource__select": "yes" if gpu else "no",
                            "gpu": 1,
                        }
                    },
                )
                self.assertEqual(
                    {d.id for d in candidates},
                    {"condor_container_gpu"} if gpu else {"pulsar_it03_tpv"},
                )

    def test_czech_alphafold_still_explicit(self):
        tool_id = "toolshed.g2.bx.psu.edu/repos/galaxy-australia/alphafold2/alphafold/2.3.1+galaxy2"
        self.assertEqual(
            [
                d.id
                for d in self.candidates(
                    tool_id,
                    site="cz-pulsar",
                    params={"model_preset": "monomer"},
                )
            ],
            ["pulsar_cz02_tpv"],
        )
        self.assertEqual(
            [d.id for d in self.candidates(site="cz-pulsar")],
            ["pulsar_cz01_tpv"],
        )

    def test_local_data_dependencies_stay_local(self):
        tools = (
            "toolshed.g2.bx.psu.edu/repos/galaxy-australia/alphafold2/alphafold/2.3.1+galaxy2",
            "toolshed.g2.bx.psu.edu/repos/bgruening/llm_hub/llm_hub/1.0",
            "toolshed.g2.bx.psu.edu/repos/bgruening/rag_retriever/rag_retriever/1.0",
            "toolshed.g2.bx.psu.edu/repos/iuc/mothur_align_seqs/mothur_align_seqs/1.0",
        )
        for tool_id in tools:
            with self.subTest(tool=tool_id):
                candidates = self.candidates(tool_id, site="it03-pulsar")
                self.assertTrue(candidates)
                self.assertFalse({d.id for d in candidates} & self.remote)

    def test_shared_tool_resources_are_loaded(self):
        candidates = self.candidates(
            "toolshed.g2.bx.psu.edu/repos/iuc/busco/busco/1.0"
        )
        # The shared database requests 16 cores / 80 GiB; local overrides do
        # not define this tool. Only three remote sites can satisfy it.
        self.assertEqual(
            {d.id for d in candidates},
            {
                "condor_container",
                "pulsar_it03_tpv",
                "pulsar_tubitak01_tpv",
                "pulsar_ufz_eve01_tpv",
            },
        )

    def test_remote_resource_limits(self):
        candidates = self.candidates(
            "toolshed.g2.bx.psu.edu/repos/iuc/kaiju_kaiju/kaiju_kaiju/1.0",
            params={"reference": "refseq_nr"},
        )
        self.assertEqual(
            {d.id for d in candidates},
            {"condor_container", "pulsar_ufz_eve01_tpv"},
        )

    def test_oom_resubmission_rechecks_remote_limits(self):
        self.assertEqual(
            {d.id for d in self.candidates(resubmitted=True)},
            {"condor_container"},
        )

    def test_remote_pulsar_failure_falls_back_to_local_once(self):
        self.assertEqual(
            {
                d.id
                for d in self.candidates(
                    site="it03-pulsar", resubmitted=True, fallback=True
                )
            },
            {"condor_container"},
        )
        local = self.candidates(
            site="it03-pulsar", resubmitted=True, fallback=True, final=True
        )
        self.assertEqual(local.id, "condor_container")
        self.assertEqual(local.runner, "htcondor")

    def test_only_non_cz_pulsar_has_fallback_resubmit(self):
        remote = self.mapper.destinations["pulsar_it03_tpv"]
        self.assertEqual(
            remote.resubmit["pulsar_local_fallback"]["condition"],
            "any_failure and attempt <= 1",
        )
        self.assertEqual(
            remote.resubmit["pulsar_local_fallback"]["environment"],
            "tpv_dispatcher",
        )
        czech = self.mapper.destinations["pulsar_cz01_tpv"]
        self.assertNotIn("pulsar_local_fallback", czech.resubmit)
        self.assertNotIn("pulsar_local_fallback", czech.params)

    def test_local_fallback_marker_survives_local_destination(self):
        destination = self.candidates(
            site="it03-pulsar", resubmitted=True, fallback=True, final=True
        )
        self.assertTrue(destination.params["pulsar_local_fallback"])

    def test_removed_site_has_meaningful_error(self):
        from galaxy.jobs.mapper import JobMappingException

        with self.assertRaisesRegex(
            JobMappingException, "Invalid 'Remote resources id'"
        ):
            self.candidates(site="removed-pulsar")

    def test_role_restrictions_and_final_parameters(self):
        destination = self.candidates(
            "interactive_tool_rstudio",
            tool_type="interactive",
            site="it03-pulsar",
            roles=("rstudio-poweruser",),
            final=True,
        )
        self.assertEqual(destination.id, "embedded_pulsar_docker")
        self.assertEqual(destination.params["submit_request_cpus"], "2")
        self.assertEqual(destination.params["submit_request_memory"], "100G")

    def test_remote_final_parameters(self):
        destination = self.candidates(site="it03-pulsar", final=True)
        self.assertEqual(destination.id, "pulsar_it03_tpv")
        self.assertEqual(destination.runner, "pulsar_eu_it03")
        self.assertEqual(destination.params["submit_request_cpus"], "1")
        self.assertEqual(destination.params["metadata_strategy"], "directory")
        self.assertEqual(destination.params["dependency_resolution"], "none")

    def test_rank_override_cannot_bypass_compatibility(self):
        for tool_id, tool_type in (
            ("interactive_tool_jupyter_notebook", "interactive"),
            ("barchart_gnuplot", "default"),
        ):
            candidates = self.candidates(
                tool_id, tool_type=tool_type, site="None", rank_override=True
            )
            self.assertTrue(candidates)
            self.assertFalse({d.id for d in candidates} & self.remote)


if __name__ == "__main__":
    unittest.main()
