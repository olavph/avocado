#!/usr/bin/env python

import copy
import unittest

from avocado.core import tree


class TestTree(unittest.TestCase):
    # Share tree with all tests
    tree = tree.create_from_yaml(['examples/mux-selftest.yaml'])

    def test_node_order(self):
        self.assertIsInstance(self.tree, tree.TreeNode)
        self.assertEqual('hw', self.tree.children[0])
        self.assertEqual({'cpu_CFLAGS': '-march=core2'},
                         self.tree.children[0].children[0].children[0].value)
        disk = self.tree.children[0].children[1]
        self.assertEqual('scsi', disk.children[0])
        self.assertEqual({'disk_type': 'scsi'}, disk.children[0].value)
        self.assertEqual('virtio', disk.children[1])
        self.assertEqual({}, disk.children[1].value)
        self.assertEqual('distro', self.tree.children[1])
        self.assertEqual('env', self.tree.children[2])
        self.assertEqual({'opt_CFLAGS': '-O2'},
                         self.tree.children[2].children[0].value)

    def test_eq(self):
        # Copy
        tree2 = copy.deepcopy(self.tree)
        self.assertEqual(self.tree, tree2)
        # Additional node
        child = tree.TreeNode("20", {'name': 'Heisenbug'})
        tree2.children[1].children[1].add_child(child)
        self.assertNotEqual(self.tree, tree2)
        # Should match again
        child.detach()
        self.assertEqual(self.tree, tree2)
        # Missing node
        tree2.children[1].children[1].detach()
        self.assertNotEqual(self.tree, tree2)
        self.assertEqual(self.tree.children[0], tree2.children[0])
        # Different value
        tree2.children[0].children[0].children[0].value = {'something': 'else'}
        self.assertNotEqual(self.tree.children[0], tree2.children[0])
        tree3 = tree.TreeNode()
        self.assertNotEqual(tree3, tree2)
        # Merge
        tree3.merge(tree2)
        self.assertEqual(tree3, tree2)
        # Add_child existing
        tree3.add_child(tree2.children[0])
        self.assertEqual(tree3, tree2)
        # Add_child incorrect class
        self.assertRaises(ValueError, tree3.add_child, 'probably_bad_type')

    def test_basic_functions(self):
        # repr
        self.assertEqual("TreeNode(name='hw')", repr(self.tree.children[0]))
        # str
        self.assertEqual("/distro/mint: init=systemv",
                         str(self.tree.children[1].children[1]))
        # len
        self.assertEqual(8, len(self.tree))  # number of leaves
        # __iter__
        self.assertEqual(8, sum((1 for _ in self.tree)))  # number of leaves
        # .root
        self.assertEqual(id(self.tree),
                         id(self.tree.children[0].children[0].children[0].root)
                         )
        # .parents
        self.assertEqual(['hw', ''], self.tree.children[0].children[0].parents)
        # environment
        self.assertEqual({}, self.tree.environment)
        self.assertEqual({'test_value': 42},
                         self.tree.children[0].environment)
        cpu = self.tree.children[0].children[0]
        self.assertEqual({'test_value': ['a']},
                         cpu.environment)
        vals = {'test_value': ['a', 'b', 'c'], 'cpu_CFLAGS': '-march=athlon64'}
        self.assertEqual(vals, cpu.children[1].environment)
        vals = {'test_value': ['a'], 'cpu_CFLAGS': '-mabi=apcs-gnu '
                '-march=armv8-a -mtune=arm8'}
        self.assertEqual(vals, cpu.children[2].environment)
        # leaves order
        leaves = ['intel', 'amd', 'arm', 'scsi', 'virtio', 'fedora', 'mint',
                  'prod']
        self.assertEqual(leaves, self.tree.get_leaves())
        # asci contain all leaves and doesn't raise any exceptions
        ascii = self.tree.get_ascii()
        for leaf in leaves:
            self.assertIn(leaf, ascii, "Leaf %s not in asci:\n%s"
                          % (leaf, ascii))

    def test_filters(self):
        tree2 = copy.deepcopy(self.tree)
        exp = ['intel', 'amd', 'arm', 'fedora', 'mint', 'prod']
        act = tree.apply_filters(tree2,
                                 filter_only=['/hw/cpu', '']).get_leaves()
        self.assertEqual(exp, act)
        tree2 = copy.deepcopy(self.tree)
        exp = ['scsi', 'virtio', 'fedora', 'mint', 'prod']
        act = tree.apply_filters(tree2,
                                 filter_out=['/hw/cpu', '']).get_leaves()
        self.assertEqual(exp, act)

    def test_merge_trees(self):
        tree2 = copy.deepcopy(self.tree)
        tree3 = tree.TreeNode()
        tree3.add_child(tree.TreeNode('hw', {'another_value': 'bbb'}))
        tree3.children[0].add_child(tree.TreeNode('nic'))
        tree3.children[0].children[0].add_child(tree.TreeNode('default'))
        tree3.children[0].children[0].add_child(tree.TreeNode('virtio',
                                                              {'nic': 'virtio'}
                                                              ))
        tree3.children[0].add_child(tree.TreeNode('cpu',
                                                  {'test_value': ['z']}))
        tree2.merge(tree3)
        exp = ['intel', 'amd', 'arm', 'scsi', 'virtio', 'default', 'virtio',
               'fedora', 'mint', 'prod']
        self.assertEqual(exp, tree2.get_leaves())
        self.assertEqual({'test_value': 42, 'another_value': 'bbb'},
                         tree2.children[0].value)
        self.assertEqual({'test_value': ['z']},
                         tree2.children[0].children[0].value)
        self.assertFalse(tree2.children[0].children[2].children[0].value)
        self.assertEqual({'nic': 'virtio'},
                         tree2.children[0].children[2].children[1].value)


class TestPathParent(unittest.TestCase):

    def test_empty_string(self):
        self.assertEqual(tree.path_parent(''), '')

    def test_on_root(self):
        self.assertEqual(tree.path_parent('/'), '')

    def test_direct_parent(self):
        self.assertEqual(tree.path_parent('/os/linux'), '/os')

    def test_false_direct_parent(self):
        self.assertNotEqual(tree.path_parent('/os/linux'), '/')

if __name__ == '__main__':
    unittest.main()
