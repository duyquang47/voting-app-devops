# Voting app with DevOps tool

## 1. ArgoCD

#### Deploy ArgoCD lên cụm:

```shell
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
kubectl create ns argocd
helm install argocd argo/argo-cd -f argocd-values.yaml -n argocd
```

#### Kiểm tra các thành phần sau apply:

```shell
kubectl get pods -n argocd
kubectl get svc -n argocd
```

#### Triển khai Application cho ArgoCD:

```shell
kubectl apply -f application-deploy.yaml
```

#### Lấy password cho user **admin**:

```shell
kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-server -o jsonpath='{.items[0].metadata.name}'
```

## 2. Jenkins

#### Tạo Docker Secret cho Jenkins sử dụng để build image:

```shell
kubectl apply -f docker-secret.yaml -n jenkins
```

#### Deploy Jenkins lên cụm:

```shell
kubectl create ns jenkins
helm repo add jenkins https://charts.jenkins.io
helm repo update
helm install jenkins jenkins/jenkins -f jenkins-values.yaml -n jenkins
```

#### Kiểm tra các thành phần sau apply:

```shell
kubectl get pods -n jenkins
kubectl get svc -n jenkins
kubectl get secret -n jenkins
```

#### Lấy password cho user **admin**:

```shell
kubectl exec --namespace jenkins $(kubectl get pods --namespace jenkins -l "app.kubernetes.io/component=jenkins-master" -o jsonpath="{.items[0].metadata.name}") -- cat /var/jenkins_home/secrets/initialAdminPassword
```

#### Truy cập Web UI và thực hiện:
- Cấu hình GitHub Webhook:
  - Vào GitHub repo
  - Thêm webhook trỏ đến Jenkins URL: `http://<JENKINS_URL>/github-webhook/`
  - Chọn trigger là **Push event**

- Tạo pipeline mới cho Jenkins: 
  - Vào **New items -> Pipeline**
  - **Source Code Management (SCM):** Cấu hình GIt với GitHub URL và chọn credential phù hợp
  - **Build triger:** Chọn GitHub hook trigger for GITScm polling
  - **Pipeline Script from SCM:** /config-repo/jenkins/Jenkinsfile

## 3. Monitoring

#### Deploy Prometheus lên cụm:

```shell
kubectl create ns monitoring
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack -f prometheus-stack-values.yaml -n monitoring
```

#### Deploy Service Monitor cho Prometheus scrape metrics app deploy lên trên cụm:

```shell 
kubectl apply -f service-monitor.yaml
```

#### Truy cập Web UI kiểm tra Target Health xem Prometheus đã scrape metrics thành công chưa

## 4. Logging

#### Tạo namespace và add các helm chart vào local repository

```shell
kubectl create ns logging
helm repo add elastic https://helm.elastic.co
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update
```

#### Deploy Elasticsearch:

```shell
helm install elasticsearch elastic/elasticsearch -f elasticsearch-values.yaml -n logging
```

#### Deploy Kibana:

```shell
helm install kibana elastic/kibana -f kibana-values.yaml -n logging
```

#### Deploy Fluent-bit:

```shell
helm install fluent-bit fluent/fluent-bit -f fluent-bit-values.yaml -n logging
```
#### Cấu hình Data View trên Kibana:
- Truy cập Web UI của Kibana service, vào ****Stack Management -> Data Views**
- Chọn **Index partern** là `fluent-bit-YYYY.MM.DD`
- Chọn **Time field** là `@timestamp`
- Lưu Data View
- Truy cập **Analytics -> Discover** để xem log 

