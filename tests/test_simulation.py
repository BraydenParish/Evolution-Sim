import os
import random
import tempfile
import unittest

from game import MAP_W, Human, QwenBrain, Simulation


class SimulationTest(unittest.TestCase):
    def setUp(self):
        # Stub out brain calls to avoid network access during tests.
        self._original_brain = QwenBrain.call_brain
        QwenBrain.call_brain = staticmethod(lambda *args, **kwargs: {"THOUGHT": "", "SPEECH": "", "CRAFT": "NONE"})
        random.seed(0)
        self.sim = Simulation()

    def tearDown(self):
        QwenBrain.call_brain = self._original_brain

    def test_ageing_death_at_40(self):
        elder = Human(99, 0, 0, tribe_id=0)
        elder.hunger = 0
        elder.years = 39
        self.sim.humans = [elder]
        self.sim.items.clear()

        self.sim.update()

        self.assertFalse(elder.alive, "Elder should die from old age at year 40")

    def test_reproduction_in_hut_creates_baby(self):
        male = Human(1, 1, 1, tribe_id=0)
        female = Human(2, 1, 1, tribe_id=0)
        male.gender = "M"
        female.gender = "F"
        male.hunger = 0
        female.hunger = 0
        self.sim.humans = [male, female]
        self.sim.items.clear()
        self.sim.structures = {(1, 1): "Hut"}

        self.sim.update()

        self.assertGreaterEqual(len(self.sim.humans), 3)
        baby = self.sim.humans[-1]
        self.assertTrue(baby.name.startswith("Baby"))
        self.assertEqual(baby.tribe_id, 0)

    def test_teaching_shares_spear_blueprint(self):
        teacher = Human(3, 0, 0, tribe_id=0)
        learner = Human(4, 0, 1, tribe_id=0)
        teacher.tools.append("SPEAR")
        learner.tools = []
        learner.memories = []
        self.sim.humans = [teacher, learner]
        self.sim.items.clear()

        self.sim.update()

        self.assertIn("Spear Blueprint", learner.memories)

    def test_mourning_triggered_on_death(self):
        fallen = Human(5, 0, 0, tribe_id=0)
        mourner = Human(6, 0, 1, tribe_id=0)
        fallen.hp = 0
        records = []
        mourner.trigger_thinking = lambda situation, async_call=True: records.append(situation)
        self.sim.humans = [fallen, mourner]
        self.sim.items.clear()

        self.sim.update()

        self.assertTrue(any("Death" in msg and "Sadness" in msg for msg in records))

    def test_migration_goal_when_no_food(self):
        hungry = Human(7, 0, 0, tribe_id=0)
        hungry.hunger = 0
        self.sim.humans = [hungry]
        self.sim.items = {k: v for k, v in self.sim.items.items() if v != "🍎"}

        self.sim.update()

        self.assertIn(0, getattr(self.sim, "migration_targets", {}))
        target = self.sim.migration_targets[0]
        prev = (hungry.x, hungry.y)
        self.sim.update()
        self.assertNotEqual(prev, (hungry.x, hungry.y))
        self.assertTrue(abs(target[0] - hungry.x) <= MAP_W - 1)

    def test_save_load_round_trip_property(self):
        self.sim.humans[0].inventory = ["🧱"]
        self.sim.humans[0].memories = ["Story"]
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name
        try:
            self.sim.save(path)
            loaded = Simulation.load(path)
            self.assertEqual(self.sim.world, loaded.world)
            self.assertEqual(len(self.sim.humans), len(loaded.humans))
            self.assertEqual(self.sim.humans[0].inventory, loaded.humans[0].inventory)
            self.assertEqual(self.sim.humans[0].memories, loaded.humans[0].memories)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
