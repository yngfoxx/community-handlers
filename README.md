# MindsDB Community Handlers

This repository contains community-maintained handlers for MindsDB.

Handlers are integrations that allow MindsDB to connect to external systems such as databases, APIs, and services. These handlers extend the MindsDB platform without requiring changes to the core codebase.

## 📦 How It Works

Each handler is implemented as a standalone module under the `community_handlers` directory, and all available handlers are listed in the `index.json` file at the root of this repository.

Note that community handlers are disabled by default in MindsDB. To enable them, set the `MINDSDB_COMMUNITY_HANDLERS` environment variable to `true`. Once enabled, community handlers can be used the same way as any other MindsDB handler.

## 🔌 Usage

Enable community handlers in MindsDB:

```
export MINDSDB_COMMUNITY_HANDLERS=true
```

Start or restart your MindsDB instance and use community handlers just like any other integration in MindsDB.

## ⚠️ Important Notice

Handlers in this repository are not officially verified or maintained by the MindsDB team.

* They may include third-party dependencies that are not reviewed under the same standards as the core MindsDB repository.
* They are provided without guarantees of reliability or long-term maintenance.
* Use them at your own discretion, especially in production environments.

For officially supported and verified integrations, refer to the [MindsDB repository](https://github.com/mindsdb/mindsdb).

## 🤝 Contributing

Contributions are welcome!

If you’d like to add a new handler or improve an existing one, create a PR to this repository, following the existing handler structure and including tests and documentation.

## 📜 License

This repository is licensed under the MIT License. See the LICENSE file for details.
