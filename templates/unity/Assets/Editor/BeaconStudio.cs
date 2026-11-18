using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class BeaconStudio
{
    private const string ScenePath = "Assets/BeaconRelay.unity";

    public static void Build()
    {
        var checkScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene);
        var game = new GameObject("Beacon Relay").AddComponent<BeaconGame>();
        if (!game.CheckScenario()) throw new InvalidOperationException("Beacon Relay scenario failed.");
        EditorSceneManager.CloseScene(checkScene, true);

        if (!File.Exists(ScenePath))
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene);
            new GameObject("Beacon Relay").AddComponent<BeaconGame>();
            if (!EditorSceneManager.SaveScene(scene, ScenePath))
                throw new IOException("Unable to save sample scene.");
        }

        var args = Environment.GetCommandLineArgs();
        int index = Array.IndexOf(args, "-studioBuildPath");
        string output = index >= 0 && index + 1 < args.Length
            ? args[index + 1]
            : ".studio/builds/BeaconRelay/BeaconRelay.exe";
        Directory.CreateDirectory(Path.GetDirectoryName(output));
        var report = BuildPipeline.BuildPlayer(new[] { ScenePath }, output,
            BuildTarget.StandaloneWindows64, BuildOptions.None);
        if (report.summary.result != BuildResult.Succeeded)
            throw new InvalidOperationException("Player build failed: " + report.summary.result);
        Debug.Log("Beacon Relay scenario and Windows build passed.");
    }
}
