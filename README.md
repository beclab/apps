# Terminus Market

This is the official repository for the Terminus Application Chart Indexer.

Terminus distributes applications in a permissionless manner using the Market Protocol, thereby maximizing the freedom of developers. Meanwhile, Terminus provides a default indexing service that is based on this repository, enhancing the flexibility and scalability of application distribution. Learn more about the [Market Protocol](https://docs.jointerminus.com/overview/protocol/market.html).


## Terminus Application Chart

The **Terminus Application Chart (TAC)** describes essential information about applications to the **Terminus OS** and **Terminus Market**. It is an extension of the Helm Chart package. Before you submit your application to **Terminus Market**, here is some information you need to know about TAC:
- [The structure of the Terminus Application Chart](https://docs.jointerminus.com/developer/develope/chart.html)
- [Configuration guide and field descriptions of TerminusManifest.yaml](https://docs.jointerminus.com/developer/develope/manifest.html)
- [Extensions field to Helm in Terminus](https://docs.jointerminus.com/developer/develope/extension.html)


## Submiting Your Application
### Brief Process

1. Test your application on Terminus,  create the TAC according to guideline.
2. Fork this repository. Add your application's TAC. Create a PR to `beclab/apps:main`.
3. Wait for GitBot to check your PR. If needed, modify PR until it passes.
4. Once the PR is merged, your application is ready to launch.


### Detail Process

#### 1. Develop and test your application
Developing applications on Terminus doesn't differ greatly from the current mainstream web development practices. You only need to grasp some basic Terminus development concepts [here](https://docs.jointerminus.com/developer/develope/).

Before submitting an application, please ensure that it has been thoroughly tested on your Terminus OS.
- Use DevBox's dev-container to test and debug your applciation in a real online environment. [Learn more about DevBox.](https://docs.jointerminus.com/developer/develope/tutorial/devbox.html)
- Use the [custom installation](https://docs.jointerminus.com/how-to/terminus/market/custom.html) in the Market app for user testing.

#### 2. Submit an application
The submission of the application needs to be completed through a Pull Request. Here's how:
- Fork this repository and add your application's TAC in your Forked repository.
- Create a `Draft PR` pointing to `beclab/apps:main`.
- Please edit your PR Title and text according to the template.
    - PR Title must in this format: [PR Type][FolderName][version]Title Content
    - `PR Type` includes:
        - NEW: Submit a new application
        - UPDATE: Update an already successfully merged application
        - REMOVE: Remove an already successfully merged application
        - SUSPEND: Suspend an already successfully merged application from distribution through the application store
    - `FolderName` is your Terminus Application Chart name. It must adhere to the naming requirements in [TAC specification](https://docs.jointerminus.com/developer/develope/chart.html).
    - `version` refers to your TAC's Chart Version, which needs to be consistent with the `version` field in `Chart.yaml` and metadata section of `TerminusManifest.yaml`
- To prevent your PR from being incorrectly parsed or closed, please adhere to the following rules:
    - Your PR title must contain only one PR Type, FolderName, and version.
    - Your PR Type must be one of the predefined types.
    - A PR should only add or modify content under the FolderName declared in the PR title.
    - Only one Open PR or Draft PR can exist at a time with the same FolderName.
    - You must be one of the owners of the folder you wish to modify. Owners are listed in the `owners` file within the chart. If you're submitting a new application, your GitHub username should be included in the `owners` file.

- During the Draft PR phase, you can continuously adjust your PR content and add new commits. Once everything is ready, click on the `Ready for review` button to submit the PR and call on GitBot to check.

> Note: The title and content of the PR are crucial for GitBot. Please adhere to the template specifications when filling them out. GitBot may automatically close any invalid PRs.


#### 3. Track your PR status
- When your PR is labeled with `PR type`, it indicates that your PR title is valid. Please **do not modify the `PR Type` afterwards.** If it doesn't reflect your intentions, simply close it and create a new one.

- You can track the progress of your PR through the status tags:
    - `waiting to submit`: your PR has an issue and requires further modification before merging.
    - `closed`: your PR is invalid or contains uncorrectable errors.
    - `waiting to merge`: Everything is progressing smoothly. Your PR has passed the check and is now awaiting auto-merge by the GitBot.
    - `merged`: your PR has been automatically merged into the indexing repository.

- If GitBot automatically closes your PR, please **do not reopen** it. This implies that the PR has irreparable issues, and GitBot had to terminate the check process. You can submit a new PR after making necessary modifications.

- When the PR is in waiting to submit state, you can continue to submit Commits to modify your PR. After submitting the Commit, GitBot will recheck your submitted TAC file and update the PR status.

- During the 'waiting to submit' state, you can continue to submit commits to modify your TAC. GitBot will recheck the TAC file and update the PR status upon receiving a new commit.

- Once your PR passes all checks, it will be automatically merged into the `beclab/apps:main`. The application will be listed on **Terminus Market** after a while.

- If you encounter any issues during the submission process, feel free to reach out to the Terminus team or seek assistance from the community.

## Managing Your Application

You can continue managing and maintaining your application by creating a Pull Request for this repository. You can upgrade your application, modify its availability, or completely remove it from the **Terminus Market**.

The process of managing applications is similar to submission.You create a specific type of Pull Request, and GitBot takes care of the rest. Terminus uses **special control files** in the root directory of TAC to manage the application's status. These **special control files** are empty files wiht specific suffix, such as `.suspend` and `.remove`

> [!NOTE]
> No ".suspend" or ".remove" files should be included in the initial submission.


### Update
When you need to update a published application, you need to create an `UPDATE` PR. 

**Please note:**
- Whenever you make changes to your TAC, such as upgrade the program, update metadata, or change owner list, be sure to upgrade your chart version.
- The chart version in the updated TAC must be ***greater than*** the current version in the repository.
- No `.suspend` or `.remove` files included in the root directory of updated TAC.
- The **Terminus Market** does not offer version rollback. If there are any issues with your application, you need to submit a new version to fix it.
- To avoid potential conflicts, we recommend syncing your fork and rebase the commits of PR to the latest main branch.


### Suspend
If for any reason you want to temporarily disable your application's download and installation from the **Terminus Market**, submit a `SUSPEND` PR.

**Please note:**
- The chart version in the submitted TAC must ***match*** the current version in the repository.
- The root directory you submit should contain the `.suspend` file and should not contain the `.remove` file.
- Once the suspend PR passes check and merges, the application store will stop listing your application.
- Users who have already downloaded and installed the application can continue to use it after suspension.

### Remove
If for any reason you want to remove your application from the **Terminus Market**, submit a `REMOVE` PR.

**Please note:**
- Completely empty the files in the current application directory and add a `.remove` file to the root directory.
- Once the remove PR passes check and merges, the application store will remove your application.
- You will not be able to reuse the same directory or TAC name in the future..
- Users who have already downloaded and installed the application can continue to use it after removal.

## Promoting Your Application

Utilizing well-organized application descriptions, screenshots, and promotional images to highlight the features and functions of your application can help attract new users in the Market. Screenshots and previews can intuitively demonstrate the user experience, helping your application stand out. 

To add promotional images on the application detail page, include links to these assets in the `promoteImage` fields within the `spec` section of the `TerminusManifest.yaml` file.

### Assets Specifications for the Terminus Market

The application's **icon** must be in PNG or WEBP format, up to 512 KB, with a size of 256x256 px.

It is highly recommended to upload at least 2 **screenshots** for promotion. **Screenshots** must be in JPEG, PNG, or WEBP format, up to 8MB each, with a size of 1440x900 px. You can upload up to 8 **screenshots**.

If you wish to have your application featured in the store, a **featured image** is required. Add a link to this image in the `featuredImage` field within the `spec` section of the `TerminusManifest.yaml` file. The image must be in JPEG, PNG, or WEBP format, up to 8MB, with a size of 1440x900 px

## Inviting Others to Collaborate

There are two ways to invite others to develop Terminus applications together:
1. Add others developer's GitHub usernames to the `owners` file. Each developer listed in `owners` can then fork the repository and submit their changes independently.
2. Add others as collaborators to your forked repository. In this case, you create the Pull Request as a representative, and all others can jointly commit to the branch that is planned to merge.