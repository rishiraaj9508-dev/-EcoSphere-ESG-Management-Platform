# Requirements Document

## Introduction

EcoSphere is a full-stack ESG (Environmental, Social, and Governance) Management Platform built with Django, SQLite, Tailwind CSS, Chart.js, and django-allauth. The platform enables organizations to track, measure, and improve their ESG performance across four core modules: Environmental, Social, Governance, and Gamification. It provides role-based access control, automated ESG score calculation, department-level tracking, comprehensive reporting, and a gamification layer to drive employee engagement. The system is designed to be mobile-responsive and deliver smart dashboard visualizations.

---

## Glossary

- **Platform**: The EcoSphere ESG Management Platform as a whole.
- **Super Admin**: The highest-privilege role; can manage all platform configuration, users, and data.
- **ESG Manager**: A role responsible for managing ESG data, reviewing submissions, and generating reports.
- **Department Head**: A role responsible for managing data and activities within a specific department.
- **Employee**: A role that participates in CSR activities, challenges, and submits data.
- **RBAC**: Role-Based Access Control — the mechanism restricting system access based on assigned roles.
- **Department**: An organizational unit to which users and ESG data are assigned.
- **Emission Factor**: A coefficient used to convert activity data (e.g., kWh) into carbon equivalent emissions (CO₂e).
- **Carbon Emission**: A calculated value (in CO₂e) representing a department's environmental impact for a given period.
- **Sustainability Goal**: A target metric for environmental performance set for a department or the organization.
- **ESG Score**: A composite numeric score (0–100) derived from Environmental (40%), Social (30%), and Governance (30%) component scores, with configurable weights.
- **CSR Activity**: A Corporate Social Responsibility initiative to which employees can be assigned and can submit participation evidence.
- **Diversity Metric**: A recorded data point representing workforce composition (e.g., gender ratio, age group distribution) for a department.
- **ESG Policy**: A governance document that employees must acknowledge within a defined review cycle.
- **Policy Acknowledgement**: A recorded confirmation by an employee that they have read and agreed to a specific ESG Policy.
- **Audit**: A governance review record capturing findings, scope, and resolution status.
- **Compliance Issue**: A governance record documenting a policy or regulatory violation, assigned to an owner with a due date.
- **Challenge**: A gamification task with a lifecycle of Draft → Active → Under Review → Completed or Archived.
- **XP (Experience Points)**: Numeric points awarded to employees for completing challenges and other actions.
- **Badge**: A digital award automatically or manually granted to employees upon meeting defined criteria.
- **Reward**: A redeemable item or benefit with a defined XP cost and stock quantity.
- **Leaderboard**: A ranked list of employees or departments ordered by XP or ESG contribution.
- **Custom Report**: A user-defined report specifying modules, date ranges, and departments, exportable as PDF, Excel, or CSV.
- **Notification**: An in-app or email message delivered to a user about a relevant platform event.
- **ESG Configuration**: Platform-level settings defining ESG Score component weights and other calculation parameters.
- **Category**: A classification label applied to CSR activities, challenges, or other entities for filtering and reporting.

---

## Requirements

### Requirement 1: User Authentication and Role-Based Access Control

**User Story:** As an organization administrator, I want a secure authentication system with role-based access control, so that each user can only access and perform the actions appropriate to their role.

#### Acceptance Criteria

1. THE Platform SHALL integrate django-allauth to handle user registration, login, logout, and password management.
2. THE Platform SHALL enforce four roles: Super Admin, ESG Manager, Department Head, and Employee.
3. WHEN a user attempts to access a view or action, THE Platform SHALL verify the user's role and deny access if the required role is not assigned.
4. THE Platform SHALL assign each user to at most one Department, with Super Admins and ESG Managers optionally spanning all departments.
5. WHEN a Super Admin creates or edits a user account, THE Platform SHALL allow the Super Admin to assign or change the user's role and department.
6. IF an unauthenticated user attempts to access a protected route, THEN THE Platform SHALL redirect the user to the login page.
7. WHEN a user logs in successfully, THE Platform SHALL redirect the user to the dashboard appropriate for their role.
8. THE Platform SHALL display navigation elements only for the sections and actions the authenticated user's role is permitted to access.

---

### Requirement 2: Department Management

**User Story:** As a Super Admin, I want to create and manage organizational departments, so that ESG data can be tracked and reported at the department level.

#### Acceptance Criteria

1. THE Platform SHALL provide a Settings interface for Super Admins to create, edit, and deactivate Departments.
2. WHEN a Department is created, THE Platform SHALL require a unique department name.
3. THE Platform SHALL associate users, Carbon Emissions, CSR Activities, and Compliance Issues with a specific Department.
4. WHEN a Department is deactivated, THE Platform SHALL retain all historical ESG data associated with that Department.
5. THE Platform SHALL display a list of all Departments with their current ESG scores and member counts on the Department management page.

---

### Requirement 3: Category Management

**User Story:** As a Super Admin or ESG Manager, I want to manage categories for ESG entities, so that activities, challenges, and policies can be organized and filtered effectively.

#### Acceptance Criteria

1. THE Platform SHALL provide a Settings interface for Super Admins and ESG Managers to create, edit, and deactivate Categories.
2. THE Platform SHALL allow a Category to be associated with CSR Activities, Challenges, and ESG Policies.
3. WHEN a Category is deactivated, THE Platform SHALL prevent new entities from being assigned to that Category while retaining existing associations.

---

### Requirement 4: ESG Configuration and Score Weights

**User Story:** As a Super Admin, I want to configure ESG score weights and platform-wide settings, so that the ESG Score reflects the organization's priorities.

#### Acceptance Criteria

1. THE Platform SHALL provide an ESG Configuration page accessible only to Super Admins.
2. THE Platform SHALL store default ESG Score weights of 40% for Environmental, 30% for Social, and 30% for Governance.
3. WHEN a Super Admin updates the ESG Score weights, THE Platform SHALL validate that the three component weights sum to exactly 100.
4. IF the submitted weights do not sum to 100, THEN THE Platform SHALL display a validation error and reject the update.
5. WHEN ESG Score weights are updated, THE Platform SHALL recalculate ESG Scores for all Departments using the new weights.
6. THE Platform SHALL persist only one active ESG Configuration record at any given time.

---

### Requirement 5: Emission Factors Configuration

**User Story:** As a Super Admin or ESG Manager, I want to configure Emission Factors, so that Carbon Emissions are calculated using accurate and up-to-date coefficients.

#### Acceptance Criteria

1. THE Platform SHALL provide an interface for Super Admins and ESG Managers to create, edit, and deactivate Emission Factors.
2. WHEN an Emission Factor is created, THE Platform SHALL require a name, unit (e.g., kWh, km, litre), and a numeric CO₂e coefficient greater than zero.
3. THE Platform SHALL display all active Emission Factors in the Environmental module settings.
4. WHEN an Emission Factor is deactivated, THE Platform SHALL prevent new Carbon Emission records from referencing it while retaining historical records.

---

### Requirement 6: Carbon Emission Tracking

**User Story:** As a Department Head or ESG Manager, I want to record and track carbon emissions for my department, so that the organization can monitor its environmental footprint.

#### Acceptance Criteria

1. THE Platform SHALL allow Department Heads and ESG Managers to create Carbon Emission records specifying department, emission source, activity value, Emission Factor, and reporting period.
2. WHEN a Carbon Emission record is saved, THE Platform SHALL automatically calculate the CO₂e value as the product of the activity value and the selected Emission Factor's coefficient.
3. THE Platform SHALL provide a toggle on each Carbon Emission record to enable or disable automatic CO₂e recalculation when the referenced Emission Factor changes.
4. WHEN a Carbon Emission record has automatic recalculation enabled and the referenced Emission Factor coefficient is updated, THE Platform SHALL recalculate and update the record's CO₂e value.
5. THE Platform SHALL display a time-series chart of Carbon Emissions per department on the Environmental Dashboard using Chart.js.
6. THE Platform SHALL aggregate Carbon Emissions by department and reporting period for use in ESG Score calculation.

---

### Requirement 7: Sustainability Goals

**User Story:** As a Super Admin or ESG Manager, I want to define and track sustainability goals, so that the organization can measure progress toward its environmental targets.

#### Acceptance Criteria

1. THE Platform SHALL allow Super Admins and ESG Managers to create Sustainability Goals specifying a target metric, target value, unit, deadline, and scope (organization-wide or department-specific).
2. WHEN a Sustainability Goal is created, THE Platform SHALL set its initial status to Active.
3. THE Platform SHALL display current progress toward each Sustainability Goal as a percentage of target value achieved.
4. WHEN a Sustainability Goal's deadline passes and the target value has not been met, THE Platform SHALL update the goal's status to Overdue.
5. WHEN a Sustainability Goal's measured value meets or exceeds the target value, THE Platform SHALL update the goal's status to Completed.
6. THE Platform SHALL display all Sustainability Goals with status, progress percentage, and deadline on the Environmental Dashboard.

---

### Requirement 8: Environmental Dashboard

**User Story:** As any authenticated user, I want a visual environmental dashboard, so that I can quickly understand the organization's and my department's environmental performance.

#### Acceptance Criteria

1. THE Platform SHALL render the Environmental Dashboard using Chart.js visualizations for Carbon Emissions trends, department comparisons, and Sustainability Goal progress.
2. THE Platform SHALL display the organization's total CO₂e emissions for the current reporting period on the Environmental Dashboard.
3. WHILE a user with the Department Head or Employee role is viewing the Environmental Dashboard, THE Platform SHALL scope all displayed data to the user's assigned Department.
4. THE Platform SHALL display a ranking of departments by CO₂e emissions on the Environmental Dashboard.
5. THE Platform SHALL make the Environmental Dashboard mobile-responsive using Tailwind CSS.

---

### Requirement 9: CSR Activities

**User Story:** As an ESG Manager or Department Head, I want to create and manage CSR activities, so that employees can participate and the organization can track social contributions.

#### Acceptance Criteria

1. THE Platform SHALL allow ESG Managers and Department Heads to create CSR Activities specifying a title, description, Category, department scope, start date, end date, and maximum participants.
2. WHEN a CSR Activity is created, THE Platform SHALL set its initial status to Upcoming.
3. WHEN the current date reaches a CSR Activity's start date, THE Platform SHALL update the activity's status to Active.
4. WHEN the current date passes a CSR Activity's end date, THE Platform SHALL update the activity's status to Closed.
5. THE Platform SHALL allow Employees to enrol in Active CSR Activities within their assigned Department.
6. WHERE the evidence toggle is enabled on a CSR Activity, THE Platform SHALL require Employees to upload evidence (file or URL) when submitting participation.
7. WHEN an Employee submits participation evidence, THE Platform SHALL set the participation record's status to Pending Review.
8. WHEN an ESG Manager or Department Head approves a participation submission, THE Platform SHALL set the participation record's status to Approved and award any configured XP to the Employee.
9. IF an Employee attempts to enrol in a CSR Activity that has reached its maximum participant limit, THEN THE Platform SHALL reject the enrolment and display an error message.

---

### Requirement 10: Diversity Metrics

**User Story:** As an ESG Manager or Department Head, I want to record diversity metrics, so that the organization can track and report workforce composition.

#### Acceptance Criteria

1. THE Platform SHALL allow ESG Managers and Department Heads to create Diversity Metric records specifying department, metric type (e.g., gender ratio, age group), value, unit, and reporting period.
2. THE Platform SHALL display Diversity Metrics per department as charts on the Social module dashboard using Chart.js.
3. THE Platform SHALL aggregate Diversity Metrics across departments for the Social component of ESG Score calculation.

---

### Requirement 11: Training Completion Tracking

**User Story:** As an ESG Manager or Department Head, I want to record employee training completions, so that the organization can demonstrate workforce development for ESG reporting.

#### Acceptance Criteria

1. THE Platform SHALL allow ESG Managers and Department Heads to create Training records specifying title, department, training date, and a list of participating employees.
2. THE Platform SHALL track completion status per employee per Training record.
3. THE Platform SHALL display training completion rates per department on the Social module dashboard.
4. THE Platform SHALL include training completion data in the Social component of ESG Score calculation.

---

### Requirement 12: ESG Policies

**User Story:** As a Super Admin or ESG Manager, I want to create and manage ESG Policies, so that employees are informed of governance requirements and acknowledgements are tracked.

#### Acceptance Criteria

1. THE Platform SHALL allow Super Admins and ESG Managers to create ESG Policies specifying a title, description, Category, version, effective date, and review cycle (in days).
2. WHEN an ESG Policy is published, THE Platform SHALL set its status to Active and notify all relevant employees via Notification.
3. THE Platform SHALL allow Super Admins and ESG Managers to create new versions of an existing ESG Policy, setting the previous version's status to Superseded.
4. WHEN a new ESG Policy version is published, THE Platform SHALL reset all existing Policy Acknowledgements for that policy and send acknowledgement-required Notifications to relevant employees.
5. THE Platform SHALL display the acknowledgement completion rate for each ESG Policy on the Governance dashboard.
6. WHEN an Employee acknowledges an ESG Policy, THE Platform SHALL record a Policy Acknowledgement with a timestamp and the employee's identity.

---

### Requirement 13: Audits

**User Story:** As a Super Admin or ESG Manager, I want to record and manage governance audits, so that audit findings are documented and tracked to resolution.

#### Acceptance Criteria

1. THE Platform SHALL allow Super Admins and ESG Managers to create Audit records specifying title, scope, auditor, audit date, findings, and status (Planned, In Progress, Completed).
2. WHEN an Audit is created, THE Platform SHALL set its initial status to Planned.
3. THE Platform SHALL allow ESG Managers to update the Audit status and attach resolution notes.
4. THE Platform SHALL display a list of all Audits with status and audit date on the Governance dashboard.
5. THE Platform SHALL include the count of Completed versus total Audits in the Governance component of ESG Score calculation.

---

### Requirement 14: Compliance Issues

**User Story:** As a Super Admin or ESG Manager, I want to create and track compliance issues, so that governance violations are owned, actioned, and resolved promptly.

#### Acceptance Criteria

1. THE Platform SHALL allow Super Admins and ESG Managers to create Compliance Issues specifying title, description, department, owner (user), due date, severity, and status (Open, In Progress, Resolved).
2. WHEN a Compliance Issue is created, THE Platform SHALL send a Notification to the assigned owner.
3. WHEN the current date passes a Compliance Issue's due date and the status is not Resolved, THE Platform SHALL flag the issue as Overdue and send a reminder Notification to the owner and the ESG Manager.
4. THE Platform SHALL display all Overdue Compliance Issues prominently on the Governance dashboard.
5. WHEN the owner updates a Compliance Issue's status to Resolved, THE Platform SHALL record the resolution timestamp.
6. THE Platform SHALL include the ratio of Resolved to total Compliance Issues in the Governance component of ESG Score calculation.

---

### Requirement 15: Gamification — Challenges

**User Story:** As an ESG Manager, I want to create and manage gamification challenges, so that employees are engaged and motivated to contribute to ESG goals.

#### Acceptance Criteria

1. THE Platform SHALL allow ESG Managers to create Challenges specifying title, description, Category, XP reward, start date, end date, and target audience (all employees or specific departments).
2. WHEN a Challenge is created, THE Platform SHALL set its initial status to Draft.
3. WHEN an ESG Manager activates a Challenge, THE Platform SHALL transition the Challenge status from Draft to Active and notify eligible employees via Notification.
4. WHEN the Challenge end date passes, THE Platform SHALL transition the Challenge status from Active to Under Review.
5. WHEN an ESG Manager marks a Challenge as reviewed and approved, THE Platform SHALL transition the Challenge status to Completed and award XP to all eligible completing employees.
6. WHEN an ESG Manager archives a Challenge, THE Platform SHALL transition the Challenge status to Archived and prevent further employee enrolments.
7. THE Platform SHALL allow Employees to enrol in Active Challenges within their target audience.
8. THE Platform SHALL allow Employees to submit completion evidence for an Active Challenge they are enrolled in.

---

### Requirement 16: XP System

**User Story:** As an employee, I want to earn XP for completing challenges and activities, so that I am recognized for my ESG contributions.

#### Acceptance Criteria

1. WHEN an Employee's Challenge completion is approved, THE Platform SHALL add the Challenge's configured XP reward to the Employee's total XP balance.
2. WHEN an Employee's CSR Activity participation is approved, THE Platform SHALL add the configured XP reward to the Employee's total XP balance.
3. THE Platform SHALL maintain a ledger of all XP transactions per Employee, recording the source, amount, and timestamp.
4. THE Platform SHALL display the Employee's current XP balance and transaction history on the Employee's profile page.

---

### Requirement 17: Badges

**User Story:** As an employee, I want to earn badges for reaching milestones, so that my achievements are visibly recognized on the platform.

#### Acceptance Criteria

1. THE Platform SHALL allow Super Admins and ESG Managers to define Badges specifying a name, description, icon, and award criteria (e.g., XP threshold, number of challenges completed, specific category participation).
2. WHERE the auto-award toggle is enabled on a Badge, THE Platform SHALL automatically evaluate all employees against the Badge's criteria and award the Badge when criteria are met.
3. WHEN a Badge is awarded to an Employee (automatically or manually), THE Platform SHALL send the Employee a Badge unlock Notification.
4. THE Platform SHALL display all earned Badges on the Employee's profile page.
5. WHEN a Super Admin or ESG Manager manually awards a Badge to an Employee, THE Platform SHALL record the awarding user and timestamp.

---

### Requirement 18: Rewards and Redemption

**User Story:** As an employee, I want to redeem my XP for rewards, so that my contributions translate into tangible benefits.

#### Acceptance Criteria

1. THE Platform SHALL allow Super Admins and ESG Managers to create Rewards specifying a name, description, XP cost, and stock quantity.
2. THE Platform SHALL display all available Rewards with their XP cost and remaining stock to authenticated employees.
3. WHEN an Employee submits a Reward redemption request, THE Platform SHALL verify that the Employee's XP balance is greater than or equal to the Reward's XP cost and that the stock quantity is greater than zero.
4. WHEN a Reward redemption is validated, THE Platform SHALL deduct the XP cost from the Employee's balance, decrement the Reward's stock quantity by one, and record the redemption transaction.
5. IF an Employee's XP balance is insufficient or the Reward stock is zero, THEN THE Platform SHALL reject the redemption and display an appropriate error message.
6. WHEN a Reward's stock quantity reaches zero, THE Platform SHALL mark the Reward as Out of Stock and prevent further redemption requests.

---

### Requirement 19: Leaderboards

**User Story:** As any authenticated user, I want to view leaderboards, so that I can see how employees and departments rank by ESG contribution and XP.

#### Acceptance Criteria

1. THE Platform SHALL display an Employee Leaderboard ranking employees by total XP in descending order.
2. THE Platform SHALL display a Department ESG Leaderboard ranking departments by their current ESG Score in descending order.
3. WHILE a user with the Employee role is viewing the Leaderboard, THE Platform SHALL highlight the current user's ranking position.
4. THE Platform SHALL refresh Leaderboard data at least once per day.
5. THE Platform SHALL display the top 10 entries on each Leaderboard by default, with the option to view the full list.

---

### Requirement 20: ESG Score Calculation

**User Story:** As an ESG Manager or Super Admin, I want an automatically calculated ESG Score for each department, so that I can objectively measure and compare ESG performance.

#### Acceptance Criteria

1. THE Platform SHALL calculate an ESG Score for each Department as the weighted sum of the Environmental, Social, and Governance component scores using the active ESG Configuration weights.
2. WHEN any underlying ESG data (Carbon Emissions, CSR participations, Audit completions, Compliance Issue resolutions) is updated, THE Platform SHALL recalculate the affected Department's component score and overall ESG Score.
3. THE Platform SHALL normalize each component score to a 0–100 scale before applying weights.
4. THE Platform SHALL calculate the Environmental component score based on Carbon Emission reduction progress against Sustainability Goals.
5. THE Platform SHALL calculate the Social component score based on CSR Activity participation rates, Training completion rates, and Diversity Metric records.
6. THE Platform SHALL calculate the Governance component score based on Policy Acknowledgement completion rates, Audit completion ratios, and Compliance Issue resolution ratios.
7. THE Platform SHALL display the current ESG Score for each Department on the main dashboard and department detail pages.

---

### Requirement 21: Main Dashboard

**User Story:** As any authenticated user, I want a smart main dashboard, so that I can get an at-a-glance view of overall ESG performance and key metrics.

#### Acceptance Criteria

1. THE Platform SHALL display the organization's overall ESG Score and each component score (Environmental, Social, Governance) on the main dashboard using Chart.js visualizations.
2. THE Platform SHALL display the Department ESG Leaderboard on the main dashboard.
3. THE Platform SHALL display a summary of open Compliance Issues, active Challenges, and upcoming CSR Activities on the main dashboard.
4. WHILE a user with the Department Head or Employee role is viewing the main dashboard, THE Platform SHALL scope ESG Score and data summaries to the user's assigned Department.
5. THE Platform SHALL make the main dashboard mobile-responsive using Tailwind CSS.
6. THE Platform SHALL refresh dashboard data on each page load.

---

### Requirement 22: Environmental Report

**User Story:** As an ESG Manager or Super Admin, I want to generate an Environmental Report, so that I can share environmental performance data with stakeholders.

#### Acceptance Criteria

1. THE Platform SHALL allow ESG Managers and Super Admins to generate an Environmental Report covering a specified date range and set of Departments.
2. THE Environmental Report SHALL include total CO₂e emissions by department, Emission Factor usage summary, and Sustainability Goal progress.
3. THE Platform SHALL export the Environmental Report in PDF, Excel, and CSV formats.

---

### Requirement 23: Social Report

**User Story:** As an ESG Manager or Super Admin, I want to generate a Social Report, so that I can share social performance data with stakeholders.

#### Acceptance Criteria

1. THE Platform SHALL allow ESG Managers and Super Admins to generate a Social Report covering a specified date range and set of Departments.
2. THE Social Report SHALL include CSR Activity participation rates, Training completion rates by department, and Diversity Metric summaries.
3. THE Platform SHALL export the Social Report in PDF, Excel, and CSV formats.

---

### Requirement 24: Governance Report

**User Story:** As an ESG Manager or Super Admin, I want to generate a Governance Report, so that I can share governance performance data with stakeholders.

#### Acceptance Criteria

1. THE Platform SHALL allow ESG Managers and Super Admins to generate a Governance Report covering a specified date range and set of Departments.
2. THE Governance Report SHALL include Policy Acknowledgement completion rates, Audit completion ratios, and Compliance Issue resolution rates.
3. THE Platform SHALL export the Governance Report in PDF, Excel, and CSV formats.

---

### Requirement 25: ESG Summary Report

**User Story:** As an ESG Manager or Super Admin, I want to generate a consolidated ESG Summary Report, so that I can communicate the organization's overall ESG performance.

#### Acceptance Criteria

1. THE Platform SHALL allow ESG Managers and Super Admins to generate an ESG Summary Report covering a specified date range.
2. THE ESG Summary Report SHALL include the overall ESG Score, all three component scores, top-performing departments, and key highlights from each module.
3. THE Platform SHALL export the ESG Summary Report in PDF, Excel, and CSV formats.

---

### Requirement 26: Custom Report Builder

**User Story:** As an ESG Manager or Super Admin, I want to build custom reports by selecting specific modules, date ranges, and departments, so that I can answer ad-hoc stakeholder questions.

#### Acceptance Criteria

1. THE Platform SHALL provide a Custom Report Builder interface allowing ESG Managers and Super Admins to select one or more modules (Environmental, Social, Governance, Gamification), a date range, and one or more Departments.
2. WHEN the user submits the Custom Report Builder form, THE Platform SHALL generate a report containing only the data fields corresponding to the selected modules and filters.
3. THE Platform SHALL export the Custom Report in PDF, Excel, and CSV formats.
4. WHEN a Custom Report is generated, THE Platform SHALL record the report parameters and generation timestamp for audit purposes.

---

### Requirement 27: Notification System

**User Story:** As any authenticated user, I want to receive in-app and email notifications for relevant platform events, so that I stay informed and can act promptly.

#### Acceptance Criteria

1. THE Platform SHALL deliver Notifications via in-app alerts and optionally via email, based on the user's Notification Settings.
2. THE Platform SHALL send Notifications for the following events: Compliance Issue assigned, Compliance Issue overdue reminder, CSR Activity participation approval, Challenge status change, ESG Policy published or updated, Badge unlocked, Reward redemption confirmed.
3. WHEN a Notification is created for a user, THE Platform SHALL display an unread count indicator in the navigation bar.
4. WHEN a user views a Notification, THE Platform SHALL mark the Notification as read.
5. THE Platform SHALL retain Notification history for each user for a minimum of 90 days.
6. THE Platform SHALL allow Super Admins to configure which event types generate email Notifications at the platform level.
7. WHERE a user has opted out of email Notifications for a specific event type, THE Platform SHALL suppress the email Notification for that user while still delivering the in-app Notification.

---

### Requirement 28: Notification Settings

**User Story:** As any authenticated user, I want to manage my notification preferences, so that I only receive the alerts relevant to me.

#### Acceptance Criteria

1. THE Platform SHALL provide each user with a Notification Settings page to enable or disable email Notifications per event type.
2. WHEN a user updates Notification Settings, THE Platform SHALL apply the updated preferences to all subsequently generated Notifications for that user.
3. THE Platform SHALL default to email Notifications enabled for all event types upon new user creation.

---

### Requirement 29: Mobile-Responsive Interface

**User Story:** As any authenticated user accessing the platform on a mobile device, I want a responsive interface, so that I can use all platform features effectively on any screen size.

#### Acceptance Criteria

1. THE Platform SHALL implement all pages using Tailwind CSS responsive utility classes to support viewport widths from 320px to 1920px.
2. THE Platform SHALL render navigation as a collapsible mobile menu on viewport widths below 768px.
3. THE Platform SHALL render all Chart.js visualizations as responsive, scaling to their container width.
4. THE Platform SHALL ensure all form inputs, buttons, and interactive elements have a minimum touch target size of 44×44 CSS pixels on mobile viewports.
