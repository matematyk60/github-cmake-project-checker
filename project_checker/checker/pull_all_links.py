import sys
import subprocess
import re
from project_checker.checker.filesystem import Directory
from project_checker.checker.filesystem import Report
from project_checker.checker.gitservice import GitService
from project_checker.checker.buildservice import CMakeService


def new_main(args):
    working_dir = Directory()
    for line in open(args[0]):
        try:
            process_single_project(line, working_dir)
        except subprocess.CalledProcessError:
            continue


def process_single_project(line, working_dir):
    working_dir.restore()
    repository = line.strip(' \t\n\r')
    match = re.search('/([-\w]+)/([-\w]+)', repository)
    if match is None:
        print (repository + ' does not match')
        raise RuntimeError('invalid repository ' + repository)
    user_dir_name = match.group(1)
    user_dir = working_dir.create_dir(user_dir_name)
    user_dir.restore()
    git = GitService(verbose=True)
    project_dir_name = match.group(2)
    project_dir = user_dir.relative(project_dir_name)
    project_dir.restore()
    if not git.exists():
        user_dir.restore()
        git.clone(repository)
        project_dir.restore()
    git.pull()
    branches = git.list_branches()
    for branch in branches.remotes_without_local():
        branch.checkout()
    branches = git.list_branches()
    report_dir = project_dir.create_dir('report')
    for branch in branches.local:
        project_dir.restore()
        branch.checkout()
        build_dir = project_dir.create_dir('build-' + branch.name)

        build_dir.restore()
        cmake = CMakeService(verbose=True)
        cmake.build()
        test_targets = cmake.test_targets_without_compound_all()

        report = Report(report_dir, 'report-' + branch.name)
        for target in test_targets:
            report[target.name] = target.report_result()
        report.store()

    final_report = Report(report_dir, 'final-report')
    for report in report_dir.all_partial_reports():
        report.load()
        final_report.merge(report)
    final_report.store()
    print (final_report.report)
    final_report.only_passed_tests('final-passed-report').store()


if __name__ == "__main__":
    new_main(sys.argv[1:])