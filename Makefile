.PHONY: setup-vcan bootstrap unit gallia-test iso14229-build iso14229-test qemu-check docker-build docker-test docker-portable-test stateful-ecu attack-test

setup-vcan:
	./setup_vcan.sh
bootstrap:
	./scripts/bootstrap_ubuntu.sh
unit:
	python3 -m unittest discover -s tests -v
gallia-test:
	./scripts/test_gallia_vecu.sh
iso14229-build:
	./scripts/build_iso14229.sh
iso14229-test:
	./scripts/test_iso14229.sh
qemu-check:
	./scripts/qemu_smoke.sh
docker-build:
	docker build -f Dockerfile.gallia -t can-uds-gallia:2.1.1 .
docker-test:
	./scripts/test_docker_gallia.sh
docker-portable-test:
	./scripts/run_portable_docker.sh
stateful-ecu:
	./scripts/run_stateful_ecu.sh
attack-test:
	./scripts/test_attacks.sh
