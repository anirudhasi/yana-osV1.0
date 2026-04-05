{{/*
Expand the name of the chart.
*/}}
{{- define "yana-os.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "yana-os.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart label — chart name + version.
*/}}
{{- define "yana-os.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every resource.
*/}}
{{- define "yana-os.labels" -}}
helm.sh/chart: {{ include "yana-os.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/name: {{ include "yana-os.name" . }}
{{- end }}

{{/*
Selector labels for a named component.
Usage: {{ include "yana-os.selectorLabels" (dict "name" $svcName "context" $) }}
*/}}
{{- define "yana-os.selectorLabels" -}}
app.kubernetes.io/name: {{ include "yana-os.name" .context }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
app: {{ .name }}
{{- end }}

{{/*
Full image reference for a service.
Usage: {{ include "yana-os.image" (dict "svcName" $svcName "context" $) }}
*/}}
{{- define "yana-os.image" -}}
{{- printf "%s/%s:%s" .context.Values.global.registry .svcName .context.Values.global.imageTag }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "yana-os.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "yana-os.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Standard environment variables from ConfigMap and Secrets (shared across all Django services).
*/}}
{{- define "yana-os.commonEnv" -}}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: yana-secrets
      key: POSTGRES_PASSWORD
- name: POSTGRES_USER
  valueFrom:
    secretKeyRef:
      name: yana-secrets
      key: POSTGRES_USER
- name: SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: yana-secrets
      key: DJANGO_SECRET_KEY
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: yana-secrets
      key: JWT_SECRET_KEY
- name: PII_ENCRYPTION_KEY
  valueFrom:
    secretKeyRef:
      name: yana-secrets
      key: PII_ENCRYPTION_KEY
- name: MINIO_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: yana-secrets
      key: MINIO_ACCESS_KEY
- name: MINIO_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: yana-secrets
      key: MINIO_SECRET_KEY
{{- end }}
