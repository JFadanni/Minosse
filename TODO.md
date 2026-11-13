# TODO list for the feature "User Quotas"

This file is intended as a scheme for the feature **User Quotas** that sets the maximum amount of resources available for each user.

## List of modifications:
- High priority:
    - [x] add a new file containing the list of users and their quotas (number of CPU cores and RAM): `quotas.mns`;
    - [x] add a check on the demanded resources in `msub` to prevent submission of jobs with more resources than the quota (the demon checks it again);
    - [x] add a check on the resources used by each user in the running jobs: `usedresources` in `Mutil.py`;
    - [x] allow jobs to run only if the user has enough resources: `check_for_submissions`;

- Low priority:
    - [x] add a script that can be used the write the list of users and their quotas in the file: `minosse quota` (`Mquota.py`);
    - [x] add a *force* flag in `msub` that allows to submit jobs even if the user does not have enough resources: `msub --force`;

See the Quotas section of the README for how they work.

To speed up the development process these features will be added to the feature branch and never reach the stable one.

To implement these features in the stable branch we need to wait until the new `minosse` machinery is stable.